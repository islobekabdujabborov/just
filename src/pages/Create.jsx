import React,{useEffect,useState,createElement as h} from "react";
import {api} from "../api";
import {Btn,Drop,Field} from "../components/ui";

const GENRES=["Roman","Detektiv","Fantastika","Biznes","Psixologiya","Tarix","Ta'lim","Sarguzasht","She'r"];

export default function Create() {
    const [mode, setMode] = useState("reel");
    const [values, setValues] = useState({ title: "", author: "", genre: "Roman", description: "", caption: "" });
    const [video, setVideo] = useState(null);
    const [cover, setCover] = useState(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [submitting, setSubmitting] = useState(false);

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

        try {
            setSubmitting(true);

            let bookId = null;

            if (mode === "reel" || cover) {
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

                if (created?.id) {
                    window.location.hash = "#/profile";
                }
            }

            if (mode === "book") {
                setSuccess("Kitob ma'lumotlari saqlandi.");
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

            <div className="flex gap-2 mb-6">
                <Btn cn={`px-5 py-2 text-sm ${mode === "reel" ? "" : "opacity-75"}`} on={() => setMode("reel")}>
                    Reel yaratish
                </Btn>
                <Btn v="g" cn={`px-5 py-2 text-sm ${mode === "book" ? "" : "opacity-75"}`} on={() => setMode("book")}>
                    Audio kitob yuklash
                </Btn>
            </div>

            <form onSubmit={submit} className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4 mb-6">
                    {mode === "reel" && (
                        <Drop
                            l="Video yuklash"
                            accept="video/mp4,video/webm,video/quicktime"
                            onChange={(event) => setVideo(event.target.files?.[0] || null)}
                        />
                    )}

                    <Drop
                        l="Kitob muqovasi"
                        accept="image/*"
                        onChange={(event) => setCover(event.target.files?.[0] || null)}
                    />
                </div>

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
                                accept="audio/*"
                                className="mt-1 w-full glass rounded-xl px-4 py-3 outline-none text-slate-800"
                            />
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

                    <Btn cn="w-full py-3 mt-5" on={submit}>
                        {submitting ? "Yuklanmoqda..." : mode === "reel" ? "Reel joylash" : "Kitobni saqlash"}
                    </Btn>
                </div>
            </form>
        </div>
    );
}
