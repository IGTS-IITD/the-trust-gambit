import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiRounds } from "../api.js";
import {
  EmptyState,
  Loading,
  Notice,
  PageHeader,
  Panel,
} from "../components/UI.jsx";

function getDomainName(domain) {
  if (domain && typeof domain === "object") {
    return domain.name ?? "Unspecified domain";
  }

  return domain ?? "Unspecified domain";
}

function getRoundStatus(round) {
  if (round.is_completed) return "Completed";
  if (round.starts_at) return "Started";
  return "Not started";
}

export default function Rounds() {
  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");

    apiRounds()
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error("Unexpected rounds response.");
        }

        if (!cancelled) setRounds(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Unable to load rounds.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reload]);

  const orderedRounds = useMemo(
    () =>
      [...rounds].sort((a, b) => {
        const gameComparison = String(a.game_name ?? "").localeCompare(
          String(b.game_name ?? "")
        );

        return (
          gameComparison ||
          Number(a.round_number) - Number(b.round_number)
        );
      }),
    [rounds]
  );

  return (
    <>
      <PageHeader
        eyebrow="Game record"
        title="Round by round."
        description="Explore the rounds and inspect how decisions connect participants."
        actions={
          <button
            className="btn"
            type="button"
            disabled={loading}
            onClick={() => setReload((value) => value + 1)}
          >
            {loading ? "Refreshing…" : "Refresh rounds"}
          </button>
        }
      />

      {loading ? (
        <Loading label="Loading rounds" />
      ) : error ? (
        <Notice tone="error">{error}</Notice>
      ) : (
        <Panel
          title="Available rounds"
          aside={<span className="pill">{rounds.length} listed</span>}
        >
          {orderedRounds.length === 0 ? (
            <EmptyState
              title="No rounds available."
              description="The game schedule will appear here when it becomes available."
            />
          ) : (
            <ul className="record-list">
              {orderedRounds.map((round) => (
                <li className="record" key={round.id}>
                  <div className="person">
                    <span className="avatar" aria-hidden="true">
                      {String(round.round_number).padStart(2, "0")}
                    </span>

                    <div>
                      <h2 className="record-title">
                        Round {round.round_number}
                        {round.game_name ? ` · ${round.game_name}` : ""}
                      </h2>

                      <p className="small muted" style={{ margin: 0 }}>
                        {getDomainName(round.domain)}
                        {" · "}
                        {getRoundStatus(round)}
                      </p>
                    </div>
                  </div>

                  <Link
                    className="btn"
                    to={`/rounds/${round.id}/graph`}
                    aria-label={`View delegation graph for round ${round.round_number}`}
                  >
                    View graph
                    <span aria-hidden="true">↗</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
    </>
  );
}