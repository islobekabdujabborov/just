import React, { useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, itemsFrom } from "../api";
import { Btn, ConfirmDialog, I } from "../components/ui";

export default function Profile({ nav, username }) {
  const [selected, setSelected] = useState(0);
  const [profile, setProfile] = useState(null);
  const [reels, setReels] = useState([]);
  const [audiobooks, setAudiobooks] = useState([]);
  const [likedBooks, setLikedBooks] = useState([]);
  const [isOwnProfile, setIsOwnProfile] = useState(!username);
  const [currentUserId, setCurrentUserId] = useState(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [followSubmitting, setFollowSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  useEffect(() => {
    if (!username && !getAccessToken()) {
      nav("/login");
      return;
    }
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      username ? api.get(`/users/${encodeURIComponent(username)}/`) : api.get("/auth/me/"),
      username ? Promise.resolve(null) : api.get("/reels/"),
      username ? Promise.resolve([]) : api.get("/audiobooks/").catch(() => []),
      username ? Promise.resolve([]) : api.get("/library/liked/").catch(() => []),
      username&&getAccessToken() ? api.get("/auth/me/").catch(() => null) : Promise.resolve(null),
    ])
      .then(([user, payload, audioPayload, likedPayload, currentUser]) => {
        if (!active) return;
        const userReels = username ? itemsFrom(user.reels) : itemsFrom(payload).filter(
          (reel) => (reel.author?.username || reel.u) === user.username,
        );
        setProfile(user);
        setReels(userReels);
        setAudiobooks(itemsFrom(audioPayload));
        setLikedBooks(itemsFrom(likedPayload));
        setCurrentUserId(username ? currentUser?.id || null : user.id);
        setIsOwnProfile(!username || currentUser?.id === user.id);
        setIsFollowing(Boolean(user.is_following));
      })
      .catch((reason) => {if (active) setError(reason.message);})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [nav, username]);

  const toggleFollow = async () => {
    if (!getAccessToken()) {
      nav("/login");
      return;
    }
    setFollowSubmitting(true);
    setError("");
    try {
      const path = `/users/${encodeURIComponent(profile.username)}/follow/`;
      const result = isFollowing ? await api.delete(path) : await api.post(path, {});
      setIsFollowing(result.is_following);
      setProfile((current) => ({ ...current, followers_count: result.followers_count }));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setFollowSubmitting(false);
    }
  };

  const deleteOwnedItem = async (item, type) => {
    setConfirmBusy(true);
    try {
      await api.delete(type === "reel" ? `/reels/${item.id}/` : `/audiobooks/${item.id}/`);
      if (type === "reel") {
        setReels((current) => current.filter((reel) => reel.id !== item.id));
      } else {
        setAudiobooks((current) => current.filter((audiobook) => audiobook.id !== item.id));
      }
      setConfirmTarget(null);
    } catch {
      setError(type === "reel" ? "Postni o'chirib bo'lmadi. Qayta urinib ko'ring." : "Audiokitobni o'chirib bo'lmadi. Qayta urinib ko'ring.");
    } finally {
      setConfirmBusy(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500">Profil yuklanmoqda...</p>;
  }

  if (!profile) {
    return <p className="text-sm text-rose-600">{error || "Profil topilmadi"}</p>;
  }

  const stats = [
    [profile.posts_count ?? reels.length, "Post"],
    [profile.followers_count || 0, "Obunachi"],
    [profile.following_count || 0, "Obuna"],
  ];
  const tabs = isOwnProfile ? ["Reels", "Audiokitoblar", "Yoqtirganlar"] : ["Reels"];

  return (
    <div>
      <div className="flex flex-wrap gap-5 items-center mb-6">
        {profile.avatar?<img src={profile.avatar} alt={`${profile.username} avatari`} className="h-24 w-24 rounded-full object-cover"/>:<div className="h-24 w-24 rounded-full bg-black grid place-items-center text-2xl font-black text-white">{(profile.username||"A").slice(0,1).toUpperCase()}</div>}
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
            {isOwnProfile ? <>
              <Btn on={() => nav("/create")} cn="px-5 py-2 text-sm">Kontent joylash</Btn>
              <Btn v="g" on={() => nav("/settings")} cn="px-4 py-2 text-sm">Profilni tahrirlash</Btn>
              <Btn v="g" on={() => {clearTokens();nav("/login");}} cn="px-4 py-2 text-sm">Chiqish</Btn>
            </> : <Btn onClick={toggleFollow} disabled={followSubmitting} cn="px-5 py-2 text-sm">
              {followSubmitting ? "Kutilmoqda..." : isFollowing ? "Obunani bekor qilish" : "Obuna bo'lish"}
            </Btn>}
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
            <div key={reel.id} className="relative">
              <button
                type="button"
                onClick={() => reel.book?.id && nav(`/books/${reel.book.id}`)}
                className="aspect-[3/4] w-full rounded-xl bg-slate-100 relative overflow-hidden flex items-center justify-center text-center p-3"
              >
                <span className="text-sm font-semibold text-slate-700">{reel.caption || "Reel"}</span>
              </button>
              {isOwnProfile && String(currentUserId) === String(reel.author?.id) && <button type="button" aria-label="Postni o'chirish" onClick={() => setConfirmTarget({
                title: "Postni o'chirish",
                message: "Postni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",
                onConfirm: () => deleteOwnedItem(reel, "reel"),
              })} className="absolute right-2 top-2 rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white shadow">O'chirish</button>}
            </div>
          )) : (selected === 1 ? audiobooks : likedBooks).map((item) => {
            const book = item.book || item;
            return (
              <div key={item.id} className="relative">
                <button
                  type="button"
                  onClick={() => book.id && nav(`/books/${book.id}`)}
                  className="aspect-[3/4] w-full rounded-xl bg-slate-100 relative overflow-hidden flex flex-col items-center justify-center text-center p-4"
                >
                  <I n={selected === 1 ? "play" : "heart"} s={26} />
                  <span className="mt-3 text-sm font-semibold text-slate-700">{book.title || book.t}</span>
                </button>
                {selected === 1 && isOwnProfile && String(item.created_by) === String(currentUserId) && <button type="button" aria-label="Audiokitobni o'chirish" onClick={() => setConfirmTarget({
                  title: "Audiokitobni o'chirish",
                  message: "Audiokitobni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",
                  onConfirm: () => deleteOwnedItem(item, "audiobook"),
                })} className="absolute right-2 top-2 rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white shadow">O'chirish</button>}
              </div>
            );
          })}
        </div>
      )}
      {error && <p role="alert" className="text-sm text-rose-600 mt-4">{error}</p>}
      <ConfirmDialog open={Boolean(confirmTarget)} title={confirmTarget?.title} message={confirmTarget?.message} loading={confirmBusy} onConfirm={confirmTarget?.onConfirm} onCancel={() => setConfirmTarget(null)} />
    </div>
  );
}
