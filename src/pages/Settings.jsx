import React, { useEffect, useState } from "react";
import { api, getAccessToken } from "../api";
import { Btn, Field } from "../components/ui";

const DEFAULT_PREFERENCES = {
  likeComments: true,
  newFollowers: true,
  newBooks: true,
  privateAccount: false,
};

const PREFERENCES = [
  ["likeComments", "Like va izohlar"],
  ["newFollowers", "Yangi obunachilar"],
  ["newBooks", "Yangi kitoblar"],
  ["privateAccount", "Yopiq hisob"],
];

export default function Settings() {
  const [profile, setProfile] = useState({ bio: "", location: "" });
  const [currentAvatar, setCurrentAvatar] = useState("");
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const localPrefs = (() => {
      try {
        return JSON.parse(localStorage.getItem("avobook.preferences") || "{}");
      } catch {
        return {};
      }
    })();
    setPreferences({ ...DEFAULT_PREFERENCES, ...localPrefs });

    api.get("/auth/me/")
      .then((user) => {
        const nextPrefs = { ...DEFAULT_PREFERENCES, ...(user.notification_preferences || {}) };
        setProfile({ bio: user.bio || "", location: user.location || "" });
        setCurrentAvatar(user.avatar || "");
        setPreferences(nextPrefs);
        localStorage.setItem("avobook.preferences", JSON.stringify(nextPrefs));
      })
      .catch((reason) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview("");
      return;
    }
    const url = URL.createObjectURL(avatarFile);
    setAvatarPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [avatarFile]);

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      let payload = { ...profile, notification_preferences: preferences };
      if (avatarFile) {
        payload = new FormData();
        payload.append("bio", profile.bio);
        payload.append("location", profile.location);
        payload.append("notification_preferences", JSON.stringify(preferences));
        payload.append("avatar", avatarFile);
      }
      const updated = await api.patch("/auth/me/", payload);
      setProfile({ bio: updated.bio || "", location: updated.location || "" });
      setCurrentAvatar(updated.avatar || "");
      setPreferences({ ...DEFAULT_PREFERENCES, ...(updated.notification_preferences || preferences) });
      localStorage.setItem("avobook.preferences", JSON.stringify({ ...DEFAULT_PREFERENCES, ...(updated.notification_preferences || preferences) }));
      setAvatarFile(null);
      setNotice("Profil ma'lumotlari saqlandi.");
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSaving(false);
    }
  };

  const togglePreference = async (key) => {
    const updated = { ...preferences, [key]: !(preferences[key] ?? DEFAULT_PREFERENCES[key]) };
    setPreferences(updated);
    localStorage.setItem("avobook.preferences", JSON.stringify(updated));
    if (!getAccessToken()) return;
    try {
      const result = await api.patch("/auth/me/", { notification_preferences: updated });
      setPreferences({ ...DEFAULT_PREFERENCES, ...(result.notification_preferences || updated) });
      localStorage.setItem("avobook.preferences", JSON.stringify({ ...DEFAULT_PREFERENCES, ...(result.notification_preferences || updated) }));
    } catch (reason) {
      setError(reason.message);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-extrabold mb-6 text-slate-800">Sozlamalar</h1>
      <form onSubmit={saveProfile} className="glass rounded-2xl p-5 mb-7">
        <h2 className="font-bold text-slate-800 mb-4">Profil ma'lumotlari</h2>
        <div className="flex items-center gap-4 mb-5">
          {avatarPreview||currentAvatar?<img src={avatarPreview||currentAvatar} alt="Profil avatari" className="h-16 w-16 rounded-full object-cover"/>:<span className="grid h-16 w-16 place-items-center rounded-full bg-black text-xl font-bold text-white" aria-hidden="true">A</span>}
          <label className="text-sm font-semibold">
            Avatar rasmini tanlash
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={(event)=>{
              const file=event.target.files?.[0];
              if(!file)return;
              const extension=file.name.split(".").pop()?.toLowerCase();
              if(!["jpg","jpeg","png","webp"].includes(extension)||file.size>8*1024*1024){setError("Avatar JPG, PNG yoki WebP bo'lishi va 8 MB dan oshmasligi kerak.");return;}
              setError("");
              setAvatarFile(file);
            }} className="mt-2 block w-full text-xs"/>
          </label>
        </div>
        <Field
          l="O'zim haqimda"
          ph="Qisqacha tanishtiring"
          name="bio"
          value={profile.bio}
          onChange={(event) => setProfile((current) => ({ ...current, bio: event.target.value }))}
        />
        <Field
          l="Joylashuv"
          ph="Toshkent"
          name="location"
          value={profile.location}
          onChange={(event) => setProfile((current) => ({ ...current, location: event.target.value }))}
        />
        <Btn type="submit" disabled={saving} cn="px-5 py-2.5">
          {saving ? "Saqlanmoqda..." : "O'zgarishlarni saqlash"}
        </Btn>
      </form>

      <section className="glass rounded-2xl divide-y divide-slate-200">
        {PREFERENCES.map(([key, label]) => {
          const enabled = preferences[key] ?? DEFAULT_PREFERENCES[key];
          return (
            <div key={key} className="flex items-center justify-between gap-4 px-4 py-3">
              <span className="text-sm font-medium text-slate-700">{label}</span>
              <button
                type="button"
                role="switch"
                aria-checked={enabled}
                aria-label={label}
                onClick={() => togglePreference(key)}
                className={`relative h-6 w-11 shrink-0 rounded-full transition ${enabled ? "bg-violet-600" : "bg-slate-300"}`}
              >
                <span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-all ${enabled ? "left-6" : "left-1"}`} />
              </button>
            </div>
          );
        })}
      </section>
      {error && <p role="alert" className="text-sm text-rose-600 mt-4">{error}</p>}
      {notice && <p role="status" className="text-sm text-emerald-600 mt-4">{notice}</p>}
    </div>
  );
}
