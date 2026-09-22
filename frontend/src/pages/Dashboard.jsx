import { useEffect, useRef, useState } from "react";
import { apiCurrentRound, apiSubmitAction, apiGetAllRatings } from "../api.js";

// How often to re-check the current round. Rounds advance automatically on
// the backend once their timer runs out, so polling is what makes that
// show up here without a manual page refresh.
const POLL_INTERVAL_MS = 5000;

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [round, setRound] = useState(null);
  const [delegationTargets, setDelegationTargets] = useState([]);
  const [delegationRatings, setDelegationRatings] = useState([]);
  const [secondsRemaining, setSecondsRemaining] = useState(null);

  const [actionType, setActionType] = useState("SOLVE");
  const [submittedAnswer, setSubmittedAnswer] = useState("");
  const [delegatedTo, setDelegatedTo] = useState("");

  const currentRoundIdRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await apiCurrentRound();
        setRound(res.current_round);
        setSecondsRemaining(res.current_round?.seconds_remaining ?? null);
        setDelegationTargets(res.delegation_targets || []);

        // Reset the submission form whenever the round actually changes.
        if (res.current_round?.id !== currentRoundIdRef.current) {
          currentRoundIdRef.current = res.current_round?.id ?? null;
          setActionType("SOLVE");
          setSubmittedAnswer("");
          setDelegatedTo("");
        }

        const data = await apiGetAllRatings();
        const filteredData =
          data.filter((rating) => rating.domain === res.current_round) || [];
        setDelegationRatings(filteredData);
        setError("");
      } catch (err) {
        setRound(null);
        setError(err.message || "Failed to load round");
      } finally {
        setLoading(false);
      }
    };

    setLoading(true);
    fetchData();
    const pollId = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(pollId);
  }, []);

  // Smoothly ticks the countdown down between polls instead of jumping
  // every 5 seconds. Restarts whenever the round itself changes; runs
  // continuously in between so it keeps counting down after each tick
  // without needing to re-run this effect every second.
  useEffect(() => {
    if (secondsRemaining === null) return;
    const tickId = setInterval(() => {
      setSecondsRemaining((s) => (s === null || s <= 0 ? s : s - 1));
    }, 1000);
    return () => clearInterval(tickId);
    // Deliberately keyed on round?.id, not secondsRemaining - the functional
    // updater above always reads fresh state, so re-running this every
    // second (which including secondsRemaining would cause) would just
    // thrash the interval for no benefit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [round?.id]);

  const onSubmitAction = async (e) => {
    e.preventDefault();
    setError("");
    const payload = { action_type: actionType };
    if (actionType === "SOLVE") payload.submitted_answer = submittedAnswer;
    if (actionType === "DELEGATE")
      payload.delegated_to = delegatedTo
        ? Number.parseInt(delegatedTo, 10)
        : null;
    try {
      await apiSubmitAction(payload);
      alert("Action submitted successfully! 🎉");
    } catch (err) {
      setError(err.message || "Failed to submit action");
    }
  };

  if (loading)
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-8 text-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <strong>Error:</strong> {error}
      </div>
    );
  if (!round)
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-yellow-800">
        ⏳ No active round at the moment.
      </div>
    );

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6 hover:shadow-xl transition-shadow">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <span className="text-2xl">🎯</span>
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-slate-800">Current Round</h2>
            <p className="text-sm text-slate-500">
              Round #{round.round_number}
            </p>
          </div>
          {secondsRemaining !== null && (
            <div
              className={`text-right ${
                secondsRemaining <= 10 ? "text-red-600" : "text-slate-700"
              }`}
            >
              <div className="text-2xl font-mono font-bold tabular-nums">
                {String(Math.floor(secondsRemaining / 60)).padStart(2, "0")}:
                {String(secondsRemaining % 60).padStart(2, "0")}
              </div>
              <div className="text-xs text-slate-400">time remaining</div>
            </div>
          )}
        </div>

        {secondsRemaining !== null && round.duration_seconds > 0 && (
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-4 -mt-2">
            <div
              className={`h-full transition-all duration-1000 ease-linear ${
                secondsRemaining <= 10 ? "bg-red-500" : "bg-blue-500"
              }`}
              style={{
                width: `${Math.max(
                  0,
                  Math.min(100, (secondsRemaining / round.duration_seconds) * 100)
                )}%`,
              }}
            />
          </div>
        )}

        <div className="space-y-4">
          <div className="bg-slate-50 rounded-lg p-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
              Domain
            </div>
            <div className="text-lg font-medium text-slate-800">
              {round.domain}
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100">
            <div className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
              Question
            </div>
            <div className="text-slate-800 leading-relaxed">
              {round.question_text}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6 hover:shadow-xl transition-shadow">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
            <span className="text-2xl">✅</span>
          </div>
          <h2 className="text-xl font-bold text-slate-800">Submit Action</h2>
        </div>

        <form onSubmit={onSubmitAction} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Action Type
            </label>
            <select
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
            >
              <option value="SOLVE">💡 Solve</option>
              <option value="DELEGATE">🤝 Delegate</option>
              <option value="PASS">⏭️ Pass</option>
            </select>
          </div>

          {actionType === "SOLVE" && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Your Answer
              </label>
              <input
                className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
                value={submittedAnswer}
                onChange={(e) => setSubmittedAnswer(e.target.value)}
                placeholder="Type your answer here..."
              />
            </div>
          )}

          {actionType === "DELEGATE" && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Delegate To
              </label>
              <select
                className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all outline-none"
                value={delegatedTo}
                onChange={(e) => setDelegatedTo(e.target.value)}
              >
                <option value="">Select a participant...</option>
                {delegationTargets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.username}
                    {` (Self Rating: ${
                      delegationRatings.find(
                        (rating) => rating.participant.id === d.id
                      )?.rating || "N/A"
                    })`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-lg active:scale-[0.98]"
          >
            Submit Action
          </button>
        </form>
      </div>
    </div>
  );
}
