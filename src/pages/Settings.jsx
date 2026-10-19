import React, { useEffect, useState } from "react";
import { api, getAccessToken } from "../api";
import { Btn, Field } from "../components/ui";
import { clearDownloadedAudio, getDownloadedAudio } from "../offlineAudio";

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

const saveLocalPreferences = (preferences) => {
  let playbackSpeed;
  try {
    playbackSpeed = JSON.parse(localStorage.getItem("avobook.preferences") || "{}").playbackSpeed;
  } catch {
    playbackSpeed = undefined;
  }
  localStorage.setItem("avobook.preferences", JSON.stringify({
    ...preferences,
    ...(playbackSpeed === undefined ? {} : { playbackSpeed }),
  }));
};

export default function Settings() {
  const [profile, setProfile] = useState({ bio: "", location: "" });
  const [currentAvatar, setCurrentAvatar] = useState("");
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [downloadCount, setDownloadCount] = useState(0);
  const [clearingDownloads, setClearingDownloads] = useState(false);
  const [offlineError, setOfflineError] = useState("");
  const [offlineNotice, setOfflineNotice] = useState("");

  useEffect(() => {
    const localPrefs = (() => {
      try {
        const storedPreferences = JSON.parse(localStorage.getItem("avobook.preferences") || "{}");
        if (!storedPreferences || typeof storedPreferences !== "object" || Array.isArray(storedPreferences)) return {};
        const notificationPreferences = { ...storedPreferences };
        delete notificationPreferences.playbackSpeed;
        return notificationPreferences;
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
        saveLocalPreferences(nextPrefs);
      })
      .catch((reason) => setError(reason.message));
    getDownloadedAudio()
      .then((entries) => setDownloadCount(entries.length))
      .catch((reason) => setOfflineError(reason.message));
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
      saveLocalPreferences({ ...DEFAULT_PREFERENCES, ...(updated.notification_preferences || preferences) });
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
    saveLocalPreferences(updated);
    if (!getAccessToken()) return;
    try {
      const result = await api.patch("/auth/me/", { notification_preferences: updated });
      setPreferences({ ...DEFAULT_PREFERENCES, ...(result.notification_preferences || updated) });
      saveLocalPreferences({ ...DEFAULT_PREFERENCES, ...(result.notification_preferences || updated) });
    } catch (reason) {
      setError(reason.message);
    }
  };

  const clearDownloads = async () => {
    setClearingDownloads(true);
    setOfflineError("");
    setOfflineNotice("");
    try {
      await clearDownloadedAudio();
      setDownloadCount(0);
      setOfflineNotice("Yuklab olingan audio boblar o'chirildi.");
    } catch (reason) {
      setOfflineError(reason.message || "Yuklab olingan audiolarni o'chirib bo'lmadi.");
    } finally {
      setClearingDownloads(false);
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
      <section className="glass rounded-2xl p-5 mt-7">
        <h2 className="font-bold text-slate-800">Offline audio</h2>
        <p className="mt-2 text-sm text-slate-600">Yuklab olingan boblar: {downloadCount} ta. Ko'pi bilan 20 ta bob va jami 500 MB saqlanadi.</p>
        <Btn type="button" v="g" disabled={clearingDownloads || downloadCount === 0} onClick={clearDownloads} cn="mt-4 px-4 py-2">
          {clearingDownloads ? "O'chirilmoqda..." : "Yuklab olingan audiolarni tozalash"}
        </Btn>
        {offlineError && <p role="alert" className="mt-3 text-sm text-rose-600">{offlineError}</p>}
        {offlineNotice && <p role="status" className="mt-3 text-sm text-emerald-600">{offlineNotice}</p>}
      </section>
      {error && <p role="alert" className="text-sm text-rose-600 mt-4">{error}</p>}
      {notice && <p role="status" className="text-sm text-emerald-600 mt-4">{notice}</p>}
    </div>
  );
}
