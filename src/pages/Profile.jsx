import React, { useEffect, useState } from "react";
import { api, getAccessToken, itemsFrom } from "../api";
import { Btn, I } from "../components/ui";

export default function Profile({ nav }) {
  const tabs = ["Reels", "Audiokitoblar", "Yoqtirganlar"];
  const [selected, setSelected] = useState(0);
  const [profile, setProfile] = useState(null);
  const [reels, setReels] = useState([]);
  const [audiobooks, setAudiobooks] = useState([]);
  const [likedBooks, setLikedBooks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      nav("/login");
      return;
    }

    Promise.all([
      api.get("/auth/me/"),
      api.get("/reels/"),
      api.get("/audiobooks/").catch(() => []),
      api.get("/library/liked/").catch(() => []),
    ])
      .then(([user, payload, audioPayload, likedPayload]) => {
        const ownReels = itemsFrom(payload).filter(
          (reel) => String(reel.author?.id || reel.author_id) === String(user.id),
        );
        setProfile(user);
        setReels(ownReels);
        setAudiobooks(itemsFrom(audioPayload));
        setLikedBooks(itemsFrom(likedPayload));
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [nav]);

  if (loading) {
    return <p className="text-sm text-slate-500">Profil yuklanmoqda...</p>;
  }

  if (!profile) {
    return <p className="text-sm text-rose-600">{error || "Profil topilmadi"}</p>;
  }

  const stats = [
    [profile.posts_count || reels.length, "Post"],
    [profile.followers_count || 0, "Obunachi"],
    [profile.following_count || 0, "Obuna"],
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-5 items-center mb-6">
        <div className="h-24 w-24 rounded-full bg-violet-100 grid place-items-center text-2xl font-black text-violet-700">
          {(profile.username || "A").slice(0, 1).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800">{profile.username}</h1>
          <p className="text-sm text-slate-500">{profile.bio || "Audiokitob o'quvchi"}</p>
          <div className="flex gap-5 my-3 text-sm text-slate-700">
            {stats.map(([count, label]) => (
              <div key={label}>
                <b className="font-extrabold text-slate-800">{count}</b>{" "}
                <span className="text-slate-500">{label}</span>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Btn on={() => nav("/create")} cn="px-5 py-2 text-sm">Kontent joylash</Btn>
            <Btn v="g" on={() => nav("/settings")} cn="px-4 py-2 text-sm">Profilni tahrirlash</Btn>
          </div>
        </div>
      </div>

      <div className="flex gap-2 mb-5">
        {tabs.map((tab, index) => (
          <button
            key={tab}
            type="button"
            onClick={() => setSelected(index)}
            className={`px-4 py-2 rounded-full text-sm font-semibold ${index === selected ? "bg-violet-600 text-white" : "glass text-slate-700"}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {selected === 0 && reels.length === 0 ? (
        <p className="text-sm text-slate-500">Hozircha reel yo'q.</p>
      ) : selected > 0 && (selected === 1 ? audiobooks : likedBooks).length === 0 ? (
        <p className="text-sm text-slate-500">Bu bo'limda hozircha kitob yo'q.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {selected === 0 ? reels.map((reel) => (
            <button
              key={reel.id}
              type="button"
              onClick={() => reel.book?.id && nav(`/books/${reel.book.id}`)}
              className="aspect-[3/4] rounded-xl bg-slate-100 relative overflow-hidden flex items-center justify-center text-center p-3"
            >
              <span className="text-sm font-semibold text-slate-700">{reel.caption || "Reel"}</span>
            </button>
          )) : (selected === 1 ? audiobooks : likedBooks).map((item) => {
            const book = item.book || item;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => book.id && nav(`/books/${book.id}`)}
                className="aspect-[3/4] rounded-xl bg-slate-100 relative overflow-hidden flex flex-col items-center justify-center text-center p-4"
              >
                <I n={selected === 1 ? "play" : "heart"} s={26} />
                <span className="mt-3 text-sm font-semibold text-slate-700">{book.title || book.t}</span>
              </button>
            );
          })}
        </div>
      )}
      {error && <p role="alert" className="text-sm text-rose-600 mt-4">{error}</p>}
    </div>
  );
}
