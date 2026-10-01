import React, { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Field } from "../components/ui";

const PREFERENCES = [
  ["likeComments", "Like va izohlar"],
  ["newFollowers", "Yangi obunachilar"],
  ["newBooks", "Yangi kitoblar"],
  ["privateAccount", "Yopiq hisob"],
];

export default function Settings() {
  const [profile, setProfile] = useState({ bio: "", location: "" });
  const [preferences, setPreferences] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("avobook.preferences") || "{}");
    } catch {
      return {};
    }
  });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/auth/me/")
      .then((user) => setProfile({ bio: user.bio || "", location: user.location || "" }))
      .catch((reason) => setError(reason.message));
  }, []);

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const updated = await api.patch("/auth/me/", profile);
      setProfile({ bio: updated.bio || "", location: updated.location || "" });
      setNotice("Profil ma'lumotlari saqlandi.");
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSaving(false);
    }
  };

  const togglePreference = (key) => {
    const updated = { ...preferences, [key]: !(preferences[key] ?? true) };
    setPreferences(updated);
    localStorage.setItem("avobook.preferences", JSON.stringify(updated));
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-extrabold mb-6 text-slate-800">Sozlamalar</h1>
      <form onSubmit={saveProfile} className="glass rounded-2xl p-5 mb-7">
        <h2 className="font-bold text-slate-800 mb-4">Profil ma'lumotlari</h2>
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
          const enabled = preferences[key] ?? true;
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
