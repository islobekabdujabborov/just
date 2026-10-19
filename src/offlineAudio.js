const sendAudioCacheMessage = async message => {
  if (!("serviceWorker" in navigator)) throw new Error("Bu brauzer offline audio saqlashni qo'llab-quvvatlamaydi.");
  const registration = await navigator.serviceWorker.ready;
  const worker = navigator.serviceWorker.controller || registration.active;
  if (!worker) throw new Error("Offline audio xizmati hali ishga tushmagan. Sahifani qayta yuklang.");

  return new Promise((resolve, reject) => {
    const channel = new MessageChannel();
    const timeout = setTimeout(() => {
      channel.port1.close();
      reject(new Error("Offline audio xizmati javob bermadi."));
    }, 5 * 60 * 1000);
    channel.port1.onmessage = event => {
      clearTimeout(timeout);
      channel.port1.close();
      if (event.data?.ok) resolve(event.data);
      else reject(new Error(event.data?.error || "Offline audio amalini bajarib bo'lmadi."));
    };
    worker.postMessage({ type: "AUDIO_CACHE", ...message }, [channel.port2]);
  });
};

export const getDownloadedAudio = async () => {
  const result = await sendAudioCacheMessage({ action: "list" });
  return result.entries;
};

export const downloadChapterAudio = (chapterId, url) => sendAudioCacheMessage({
  action: "download",
  chapterId,
  url: new URL(url, window.location.origin).href,
});

export const removeDownloadedAudio = chapterId => sendAudioCacheMessage({
  action: "remove",
  chapterId,
});

export const clearDownloadedAudio = () => sendAudioCacheMessage({ action: "clear" });

export const offlineAudioUrl = chapterId => `/offline-audio/chapters/${chapterId}`;
