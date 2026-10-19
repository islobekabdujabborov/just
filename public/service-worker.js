const CACHE_NAME = "avobook-shell-v1";
const AUDIO_CACHE_NAME = "avobook-audio-v1";
const MAX_AUDIO_BYTES = 100 * 1024 * 1024;
const MAX_TOTAL_AUDIO_BYTES = 500 * 1024 * 1024;
const MAX_AUDIO_ENTRIES = 20;
const APP_SHELL = [
  "/",
  "/static/manifest.webmanifest",
  "/static/icons/avobook.svg",
  "/static/icons/avobook-192.png",
  "/static/icons/avobook-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(key =>
        key.startsWith("avobook-") && key !== CACHE_NAME && key !== AUDIO_CACHE_NAME
      ).map(key => caches.delete(key)))
    )
  );
  self.clients.claim();
});

const reply = (event, message) => {
  const port = event.ports[0];
  if (port) port.postMessage(message);
};

const audioCacheKey = chapterId => new URL(`/offline-audio/chapters/${chapterId}`, self.location.origin).href;

const isCacheableAudioUrl = (value, chapterId) => {
  const url = new URL(value);
  return url.origin === self.location.origin &&
    new RegExp(`^/media-protected/chapters/${chapterId}/[^/]+/$`).test(url.pathname);
};

const audioEntries = async cache => {
  const requests = await cache.keys();
  return Promise.all(requests.map(async request => {
    const response = await cache.match(request);
    return {
      url: request.url,
      chapter_id: /^\/offline-audio\/chapters\/(\d+)$/.exec(new URL(request.url).pathname)?.[1] || null,
      size: Number(response.headers.get("Content-Length")) || 0
    };
  }));
};

const readAudioDownload = async response => {
  const declaredSize = Number(response.headers.get("Content-Length"));
  if (Number.isFinite(declaredSize) && declaredSize > MAX_AUDIO_BYTES) {
    throw new Error("Audio 100 MB dan katta; yuklab bo'lmadi.");
  }
  if (!response.body) throw new Error("Audio faylning mazmunini o'qib bo'lmadi.");

  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_AUDIO_BYTES) {
      await reader.cancel();
      throw new Error("Audio 100 MB dan katta; yuklab bo'lmadi.");
    }
    chunks.push(value);
  }
  return { blob: new Blob(chunks, { type: response.headers.get("Content-Type") || "application/octet-stream" }), size };
};

const handleAudioMessage = async event => {
  const { action, chapterId, url: value } = event.data || {};
  const cache = await caches.open(AUDIO_CACHE_NAME);

  if (action === "list") {
    reply(event, { ok: true, entries: await audioEntries(cache) });
    return;
  }
  if (action === "clear") {
    await caches.delete(AUDIO_CACHE_NAME);
    reply(event, { ok: true, entries: [] });
    return;
  }
  if (!Number.isSafeInteger(Number(chapterId)) || Number(chapterId) <= 0) {
    throw new Error("Bob identifikatori noto'g'ri.");
  }
  const key = audioCacheKey(Number(chapterId));
  if (action === "remove") {
    await cache.delete(key);
    reply(event, { ok: true, chapter_id: Number(chapterId) });
    return;
  }
  if (!value || !isCacheableAudioUrl(value, Number(chapterId))) {
    throw new Error("Audio manzili yaroqsiz yoki yuklab olish qo'llab-quvvatlanmaydi.");
  }
  const url = new URL(value, self.location.origin).href;

  if (action !== "download") throw new Error("Audio amali noma'lum.");

  const response = await fetch(url, { credentials: "same-origin" });
  if (response.status !== 200 || !response.ok) {
    throw new Error(response.status === 206
      ? "Server audio faylni qisman yubordi; uni offline saqlab bo'lmadi."
      : `Audio yuklanmadi (${response.status}).`);
  }
  const { blob, size } = await readAudioDownload(response);
  const entries = await audioEntries(cache);
  const existingEntry = entries.find(entry => Number(entry.chapter_id) === Number(chapterId));
  const previousSize = existingEntry?.size || 0;
  const totalSize = entries.reduce((total, entry) => total + entry.size, 0) - previousSize;
  const entryCount = entries.length - (existingEntry ? 1 : 0);
  if (entryCount >= MAX_AUDIO_ENTRIES) {
    throw new Error("Ko'pi bilan 20 ta bobni offline saqlash mumkin. Sozlamalardan yuklamalarni tozalang.");
  }
  if (totalSize + size > MAX_TOTAL_AUDIO_BYTES) {
    throw new Error("Offline audio uchun 500 MB joy chegarasidan oshib ketadi.");
  }
  const headers = new Headers(response.headers);
  headers.set("Content-Length", String(size));
  headers.set("Accept-Ranges", "bytes");
  headers.delete("Content-Encoding");
  await cache.put(key, new Response(blob, { status: 200, headers }));
  reply(event, { ok: true, chapter_id: Number(chapterId), size });
};

self.addEventListener("message", event => {
  if (event.data?.type !== "AUDIO_CACHE") return;
  event.waitUntil(handleAudioMessage(event).catch(error => {
    reply(event, { ok: false, error: error.message || "Offline audio amalini bajarib bo'lmadi." });
  }));
});

const rangeResponse = async (cached, rangeHeader) => {
  const body = await cached.arrayBuffer();
  const size = body.byteLength;
  const match = /^bytes=(\d*)-(\d*)$/.exec(rangeHeader.trim());
  if (!match || (!match[1] && !match[2]) || size === 0) {
    return new Response(null, {
      status: 416,
      headers: { "Content-Range": `bytes */${size}`, "Accept-Ranges": "bytes" }
    });
  }

  let start;
  let end;
  if (match[1]) {
    start = Number(match[1]);
    end = match[2] ? Number(match[2]) : size - 1;
  } else {
    const suffixLength = Number(match[2]);
    start = Math.max(size - suffixLength, 0);
    end = size - 1;
  }
  end = Math.min(end, size - 1);
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || start > end) {
    return new Response(null, {
      status: 416,
      headers: { "Content-Range": `bytes */${size}`, "Accept-Ranges": "bytes" }
    });
  }

  const headers = new Headers(cached.headers);
  headers.delete("Content-Encoding");
  headers.set("Accept-Ranges", "bytes");
  headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
  headers.set("Content-Length", String(end - start + 1));
  return new Response(body.slice(start, end + 1), { status: 206, headers });
};

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET") return;

  const protectedChapter = /^\/media-protected\/chapters\/(\d+)\/[^/]+\/$/.exec(url.pathname);
  const offlineChapter = /^\/offline-audio\/chapters\/(\d+)$/.exec(url.pathname);
  if (protectedChapter || offlineChapter) {
    const chapterId = Number((protectedChapter || offlineChapter)[1]);
    const cacheKey = audioCacheKey(chapterId);
    event.respondWith(
      caches.open(AUDIO_CACHE_NAME).then(cache => cache.match(cacheKey)).then(cached => {
        if (cached) {
          return request.headers.has("Range")
            ? rangeResponse(cached, request.headers.get("Range"))
            : cached;
        }
        if (offlineChapter) return new Response("Offline audio not found.", { status: 404 });
        return fetch(request);
      })
    );
    return;
  }

  if (request.headers.has("Range")) {
    event.respondWith(
      caches.open(AUDIO_CACHE_NAME).then(cache => cache.match(request.url)).then(cached =>
        cached ? rangeResponse(cached, request.headers.get("Range")) : fetch(request)
      )
    );
    return;
  }

  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) caches.open(CACHE_NAME).then(cache => cache.put("/", response.clone()));
          return response;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
          return response;
        });
      })
    );
    return;
  }

  event.respondWith(
    caches.open(AUDIO_CACHE_NAME).then(cache => cache.match(request.url)).then(cached =>
      cached || fetch(request)
    )
  );
});
