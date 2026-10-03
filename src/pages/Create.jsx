import React,{useEffect,useState,createElement as h} from "react";
import {api} from "../api";
import {Btn,Drop,Field} from "../components/ui";

const GENRES=["Roman","Detektiv","Fantastika","Biznes","Psixologiya","Tarix","Ta'lim","Sarguzasht","She'r"];

function useObjectUrl(file){
    const [url,setUrl]=useState("");
    useEffect(()=>{
        if(!file){setUrl("");return;}
        const objectUrl=URL.createObjectURL(file);
        setUrl(objectUrl);
        return()=>URL.revokeObjectURL(objectUrl);
    },[file]);
    return url;
}

export default function Create() {
    const [mode, setMode] = useState("reel");
    const [values, setValues] = useState({ title: "", author: "", genre: "Roman", description: "", caption: "" });
    const [video, setVideo] = useState(null);
    const [cover, setCover] = useState(null);
    const [audioFile, setAudioFile] = useState(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const videoPreview = useObjectUrl(video);
    const coverPreview = useObjectUrl(cover);
    const audioPreview = useObjectUrl(audioFile);

    const update = (event) => {
        const { name, value } = event.target;
        setValues((previous) => ({ ...previous, [name]: value }));
    };

    const submit = async (event) => {
        event.preventDefault();
        setError("");
        setSuccess("");

        if (!values.title.trim()) {
            setError("Kitob nomi kiritilishi shart.");
            return;
        }

        if (mode === "reel" && !video) {
            setError("Reel uchun video tanlang.");
            return;
        }
        if (mode === "book" && !audioFile) {
            setError("Audiokitob uchun audio fayl tanlang.");
            return;
        }
        const extension = (file) => file?.name.split(".").pop()?.toLowerCase() || "";
        if (cover && (!(["jpg", "jpeg", "png", "webp"].includes(extension(cover))) || cover.size > 8 * 1024 * 1024)) {
            setError("Muqova JPG, PNG yoki WebP bo'lishi va 8 MB dan oshmasligi kerak.");
            return;
        }
        if (video && (!(["mp4", "mov", "webm"].includes(extension(video))) || video.size > 100 * 1024 * 1024)) {
            setError("Video MP4, MOV yoki WebM bo'lishi va 100 MB dan oshmasligi kerak.");
            return;
        }
        if (audioFile && (!(["mp3", "m4a", "wav", "ogg"].includes(extension(audioFile))) || audioFile.size > 100 * 1024 * 1024)) {
            setError("Audio MP3, M4A, WAV yoki OGG bo'lishi va 100 MB dan oshmasligi kerak.");
            return;
        }

        try {
            setSubmitting(true);

            let bookId = null;

            if (mode === "reel" || mode === "book") {
                const bookPayload = new FormData();
                bookPayload.append("title", values.title);
                bookPayload.append("author_name", values.author || "Noma'lum muallif");
                bookPayload.append("genre", values.genre);
                bookPayload.append("description", values.description || "");
                bookPayload.append("language", "uz");
                if (cover) {
                    bookPayload.append("cover", cover);
                }

                const bookResult = await api.post("/books/", bookPayload);
                bookId = bookResult.id;
            }

            if (mode === "reel") {
                const reelPayload = new FormData();
                reelPayload.append("caption", values.caption || `${values.title} haqida qisqa taassurot`);
                reelPayload.append("book_id", String(bookId || 0));
                reelPayload.append("video", video);

                const created = await api.post("/reels/", reelPayload);
                setSuccess("Reel muvaffaqiyatli yuklandi.");
                setValues({ title: "", author: "", genre: "Roman", description: "", caption: "" });
                setVideo(null);
                setCover(null);
                setAudioFile(null);

            }

            if (mode === "book") {
                const audioPayload = new FormData();
                audioPayload.append("book_id", String(bookId));
                audioPayload.append("audio_file", audioFile);
                await api.post("/audiobooks/", audioPayload);
                setSuccess("Kitob ma'lumotlari saqlandi.");
                setValues({ title: "", author: "", genre: "Roman", description: "", caption: "" });
                setCover(null);
                setAudioFile(null);
            }
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div>
            <h1 className="text-3xl font-extrabold mb-5">Yaratish</h1>

            <div className="flex flex-wrap gap-2 mb-6">
                <Btn disabled={submitting} cn={`px-5 py-2 text-sm ${mode === "reel" ? "" : "opacity-75"}`} on={() => setMode("reel")}>
                    Reel yaratish
                </Btn>
                <Btn v="g" disabled={submitting} cn={`px-5 py-2 text-sm ${mode === "book" ? "" : "opacity-75"}`} on={() => setMode("book")}>
                    Audio kitob yuklash
                </Btn>
            </div>

            <form onSubmit={submit} className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4 mb-6">
                    {mode === "reel" && (
                        <Drop
                            l="Video yuklash"
                            key={video?.name||"video"}
                            accept=".mp4,.mov,.webm,video/mp4,video/webm,video/quicktime"
                            onChange={(event) => setVideo(event.target.files?.[0] || null)}
                        />
                    )}

                    <Drop
                        l="Kitob muqovasi"
                        key={cover?.name||"cover"}
                        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                        onChange={(event) => setCover(event.target.files?.[0] || null)}
                    />
                </div>

                {videoPreview&&<video src={videoPreview} controls muted playsInline preload="metadata" className="mb-4 max-h-72 w-full rounded-xl bg-black object-contain" aria-label="Tanlangan video ko'rinishi"/>}
                {coverPreview&&<img src={coverPreview} alt="Tanlangan kitob muqovasi" className="mb-4 h-40 w-32 rounded-xl object-cover"/>}

                <div className="glass rounded-3xl p-5">
                    <Field
                        l="Kitob nomi"
                        ph="Masalan: O'tkan kunlar"
                        name="title"
                        value={values.title}
                        onChange={update}
                        required
                    />

                    <Field
                        l="Muallif"
                        ph="Abdulla Qodiriy"
                        name="author"
                        value={values.author}
                        onChange={update}
                    />

                    <label className="block mb-4">
                        <span className="text-xs text-slate-600">Janr</span>
                        <select
                            name="genre"
                            value={values.genre}
                            onChange={update}
                            className="mt-1 w-full glass rounded-xl px-4 py-3 outline-none bg-white text-slate-800"
                        >
                            {GENRES.map((genre) => (
                                <option key={genre} value={genre}>
                                    {genre}
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="block mb-4">
                        <span className="text-xs text-slate-600">Tavsif</span>
                        <textarea
                            name="description"
                            rows={3}
                            value={values.description}
                            onChange={update}
                            className="mt-1 w-full glass rounded-xl px-4 py-3 outline-none text-slate-800"
                        />
                    </label>

                    {mode === "reel" && (
                        <label className="block mb-4">
                            <span className="text-xs text-slate-600">Reel izohi</span>
                            <textarea
                                name="caption"
                                rows={2}
                                value={values.caption}
                                onChange={update}
                                className="mt-1 w-full glass rounded-xl px-4 py-3 outline-none text-slate-800"
                            />
                        </label>
                    )}

                    {mode === "book" && (
                        <label className="block mb-4">
                            <span className="text-xs text-slate-600">Audio fayl (mp3)</span>
                            <input
                                type="file"
                                key={audioFile?.name||"audio"}
                                accept=".mp3,.m4a,.wav,.ogg,audio/mpeg,audio/mp4,audio/wav,audio/ogg"
                                onChange={(event) => setAudioFile(event.target.files?.[0] || null)}
                                className="mt-1 w-full glass rounded-xl px-4 py-3 outline-none text-slate-800"
                            />
                            {audioPreview&&<audio src={audioPreview} controls preload="metadata" className="mt-3 w-full" aria-label="Tanlangan audio ko'rinishi"/>}
                        </label>
                    )}

                    {error && (
                        <p role="alert" className="text-sm text-rose-300 mb-3">
                            {error}
                        </p>
                    )}

                    {success && (
                        <p role="status" className="text-sm text-emerald-500 mb-3">
                            {success}
                        </p>
                    )}

                    <Btn type="submit" disabled={submitting} cn="w-full py-3 mt-5">
                        {submitting ? "Yuklanmoqda..." : mode === "reel" ? "Reel joylash" : "Kitobni saqlash"}
                    </Btn>
                </div>
            </form>
        </div>
    );
}
