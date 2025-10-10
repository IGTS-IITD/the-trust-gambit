import { useEffect, useState } from "react";
import {
  apiGetProfile,
  apiGetHostels,
  apiUpdateProfileHostel,
  setParticipantId,
} from "../api.js";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [hostels, setHostels] = useState([]);
  const [hostelId, setHostelId] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    apiGetProfile()
      .then((p) => {
        setProfile(p);
        setParticipantId(p.id);
        setHostelId(p.hostel?.id || "");
      })
      .catch(() => {});
    apiGetHostels()
      .then(setHostels)
      .catch(() => {});
  }, []);

  const onSave = async () => {
    setStatus("");
    try {
      await apiUpdateProfileHostel(
        hostelId ? Number.parseInt(hostelId, 10) : null
      );
      setStatus("Saved!");
    } catch (err) {
      setStatus(err.message || "Failed to save");
    }
  };

  if (!profile)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-slate-100" />
          <div className="h-6 w-32 bg-slate-100 rounded" />
        </div>
        <div className="space-y-2 animate-pulse">
          <div className="h-10 bg-slate-100 rounded" />
          <div className="h-10 bg-slate-100 rounded" />
          <div className="h-10 bg-slate-100 rounded" />
        </div>
      </div>
    );

  const ok = status && status.toLowerCase().includes("saved");
  const initials = (profile.user?.username || "").slice(0, 2).toUpperCase();
  const dirty = String(hostelId || "") !== String(profile.hostel?.id || "");

  return (
    <div className="max-w-xl mx-auto px-4 py-10">
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-700 grid place-items-center border border-indigo-100 font-semibold">
              {initials}
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-800">Profile</h1>
              <p className="text-xs text-slate-500">
                Manage your account and hostel
              </p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-slate-700 border border-slate-200">
              ID: {profile.id}
            </span>
            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-slate-700 border border-slate-200">
              {profile.hostel?.name || "No hostel"}
            </span>
          </div>
        </div>

        <div className="grid gap-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Username
              </div>
              <div className="font-medium text-slate-800">
                {profile.user?.username}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Email
              </div>
              <div className="text-slate-700">{profile.user?.email || "—"}</div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Hostel
            </label>
            <select
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              value={hostelId}
              onChange={(e) => setHostelId(e.target.value)}
              aria-label="Select your hostel"
            >
              <option value="">None</option>
              {hostels.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-1">
              Choose a hostel to appear on the leaderboard and profile.
            </p>
            {hostelId && (
              <div className="mt-2">
                <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 border border-slate-200">
                  Selected:{" "}
                  {hostels.find((h) => String(h.id) === String(hostelId))?.name}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-center gap-4">
            <button
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={onSave}
              disabled={!dirty}
            >
              💾 Save
            </button>
            {status && (
              <div
                role="status"
                className={`text-sm rounded-lg px-3 py-1.5 border ${
                  ok
                    ? "bg-green-50 text-green-700 border-green-200"
                    : "bg-red-50 text-red-700 border-red-200"
                }`}
              >
                {status}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
