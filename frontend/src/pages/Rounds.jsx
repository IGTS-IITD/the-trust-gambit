import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRounds } from "../api.js";

export default function Rounds() {
  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    apiRounds()
      .then(setRounds)
      .catch((e) => setError(e.message || "Failed to load rounds"))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🧩</span>
          <h1 className="text-xl font-semibold text-slate-800">Rounds</h1>
        </div>
        <div className="space-y-3 animate-pulse">
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
          <span className="text-2xl">🧩</span>
          <h1 className="text-xl font-semibold text-slate-800">Rounds</h1>
        </div>
        <div className="text-sm text-slate-500">
          {rounds.length} round{rounds.length === 1 ? "" : "s"}
        </div>
      </div>

      {rounds.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <div className="text-3xl mb-2">🕹️</div>
          <p className="text-slate-700 font-medium">No rounds available</p>
          <p className="text-slate-500 text-sm">Please check back later.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {rounds.map((r) => (
            <li
              key={r.id}
              className="group flex items-center justify-between gap-4 px-4 py-3 rounded-lg border border-slate-200 hover:bg-slate-50 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-10 h-10 grid place-items-center rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-100 text-lg">
                  #{r.round_number}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-slate-800 truncate">
                    Round {r.round_number}
                  </div>
                  <div>
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 border border-slate-200">
                      {r.domain}
                    </span>
                  </div>
                </div>
              </div>

              <Link
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 font-medium hover:bg-slate-50 hover:shadow-sm active:scale-[0.98] transition-all"
                to={`/rounds/${r.id}/graph`}
              >
                View Graph
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
