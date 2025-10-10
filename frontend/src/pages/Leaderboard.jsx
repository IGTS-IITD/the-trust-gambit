import { useEffect, useState } from "react";
import { apiLeaderboard } from "../api.js";

export default function Leaderboard() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    apiLeaderboard()
      .then(setRows)
      .catch((e) => setError(e.message || "Failed to load leaderboard"))
      .finally(() => setLoading(false));
  }, []);

  const rankBadge = (i) => {
    const rank = i + 1;
    if (rank === 1)
      return {
        cls: "bg-yellow-100 text-yellow-700 border-yellow-300",
        content: "🥇",
      };
    if (rank === 2)
      return {
        cls: "bg-slate-100 text-slate-700 border-slate-300",
        content: "🥈",
      };
    if (rank === 3)
      return {
        cls: "bg-amber-100 text-amber-700 border-amber-300",
        content: "🥉",
      };
    return {
      cls: "bg-slate-100 text-slate-600 border-slate-200",
      content: String(rank),
    };
  };

  const initials = (name = "") => name.trim().slice(0, 2).toUpperCase();

  if (loading)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🏆</span>
          <h1 className="text-xl font-semibold text-slate-800">Leaderboard</h1>
        </div>
        <div className="space-y-3 animate-pulse">
          <div className="h-12 bg-slate-100 rounded-lg" />
          <div className="h-12 bg-slate-100 rounded-lg" />
          <div className="h-12 bg-slate-100 rounded-lg" />
          <div className="h-12 bg-slate-100 rounded-lg" />
        </div>
      </div>
    );

  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <strong>Error:</strong> {error}
      </div>
    );

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏆</span>
          <h1 className="text-xl font-semibold text-slate-800">Leaderboard</h1>
        </div>
        <div className="text-sm text-slate-500">
          {rows.length} player{rows.length === 1 ? "" : "s"}
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <div className="text-3xl mb-2">🕹️</div>
          <p className="text-slate-700 font-medium">No scores yet</p>
          <p className="text-slate-500 text-sm">Play a round to appear here.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-200">
          {rows.map((r, idx) => {
            const badge = rankBadge(idx);
            const name = r.participant?.username || "Player";
            return (
              <li
                key={idx}
                className="group flex items-center justify-between gap-4 py-3 px-2 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <span
                    className={`w-9 h-9 grid place-items-center rounded-full border text-base font-semibold ${badge.cls}`}
                  >
                    {badge.content}
                  </span>

                  <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 grid place-items-center font-semibold border border-blue-200">
                    {initials(name)}
                  </div>

                  <div className="min-w-0">
                    <div className="font-medium text-slate-800 truncate">
                      {name}
                    </div>
                    <div className="text-xs text-slate-500">Participant</div>
                  </div>
                </div>

                <div className="shrink-0">
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                    {r.score}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
