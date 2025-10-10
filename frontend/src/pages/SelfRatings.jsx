import { useEffect, useState } from "react";
import { apiGetDomains, apiGetProfile, apiGetSelfRatings } from "../api.js";
import { getParticipantId, apiPostSelfRatings } from "../api.js";

export default function SelfRatings() {
  const [domains, setDomains] = useState([]);
  const [selfRatings, setSelfRatings] = useState([]);
  const [participantId, setPid] = useState(getParticipantId());
  const [domainId, setDomainId] = useState("");
  const [rating, setRating] = useState(5);
  const [justification, setJustification] = useState("");
  const [status, setStatus] = useState("");

  const loadDomains = async () => {
    try {
      const d = await apiGetDomains();
      setDomains(d);
    } catch {
      setDomains([]);
    }
  };

  const loadSelfRatings = async () => {
    try {
      const list = await apiGetSelfRatings();
      setSelfRatings(list || []);
    } catch {
      setSelfRatings([]);
    }
  };

  useEffect(() => {
    loadDomains();
    loadSelfRatings();
    if (!participantId) {
      apiGetProfile()
        .then((p) => setPid(p.id))
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setStatus("");
    if (!participantId) {
      setStatus("Missing participant id.");
      return;
    }
    try {
      await apiPostSelfRatings({
        participant: participantId,
        domain: Number.parseInt(domainId, 10),
        rating: Number(rating),
        justification,
      });
      setStatus("Submitted!");
      setDomainId("");
      setRating(5);
      setJustification("");
      await loadSelfRatings();
    } catch (err) {
      setStatus(err.message || "Failed to submit");
    }
  };

  const domainName = (id) =>
    domains.find((d) => d.id === id)?.name || `Domain #${id}`;

  const ok = status && status.toLowerCase().includes("submitted");

  return (
    <div className="max-w-xl mx-auto px-4 py-10">
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 grid place-items-center border border-indigo-100">
            ⭐
          </div>
          <h1 className="text-xl font-semibold text-slate-800">Self Ratings</h1>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Domain
            </label>
            <select
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              value={domainId}
              onChange={(e) => setDomainId(e.target.value)}
              required
            >
              <option value="">Select domain</option>
              {domains.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Rating (0-10)
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              type="number"
              min="0"
              max="10"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Justification
            </label>
            <textarea
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              rows="4"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              required
            />
          </div>

          {status && (
            <div
              className={`text-sm rounded-lg px-3 py-2 border ${
                ok
                  ? "bg-green-50 text-green-700 border-green-200"
                  : "bg-red-50 text-red-700 border-red-200"
              }`}
            >
              {status}
            </div>
          )}

          <button
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-lg active:scale-[0.98]"
            type="submit"
          >
            Submit Rating
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6 mt-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-slate-800">
            Your submitted ratings
          </h2>
          {selfRatings.length > 0 && (
            <span className="text-sm text-slate-500">
              {selfRatings.length} item{selfRatings.length === 1 ? "" : "s"}
            </span>
          )}
        </div>

        {selfRatings.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
            <div className="text-3xl mb-2">📝</div>
            <p className="text-slate-700 font-medium">No ratings yet</p>
            <p className="text-slate-500 text-sm">
              Submit your first self-rating above.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {selfRatings.map((r) => (
              <li
                key={r.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="min-w-0">
                  <div className="font-medium text-slate-800">
                    {domainName(r.domain)}
                  </div>
                  <div className="text-sm text-slate-600 line-clamp-3">
                    {r.justification}
                  </div>
                </div>
                <span className="shrink-0 inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-sm font-semibold text-slate-700 border border-slate-200">
                  {r.rating}/10
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
