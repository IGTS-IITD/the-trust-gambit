import { useEffect, useMemo, useState } from "react";
import { apiLeaderboard } from "../api.js";
import {
  EmptyState,
  Loading,
  Notice,
  PageHeader,
  Panel,
  formatScore,
  initials,
} from "../components/UI.jsx";

export default function Leaderboard() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");

    apiLeaderboard()
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error("Unexpected leaderboard response.");
        }

        if (!cancelled) setRows(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Unable to load the standings.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reload]);

  const rankedRows = useMemo(() => {
    const sorted = [...rows].sort(
      (a, b) => Number(b.score) - Number(a.score)
    );

    let rank = 0;

    return sorted.map((row, index) => {
      if (
        index === 0 ||
        Number(row.score) !== Number(sorted[index - 1].score)
      ) {
        rank = index + 1;
      }

      return { ...row, rank };
    });
  }, [rows]);

  const visibleRows = rankedRows.filter((row) =>
    String(row.participant?.username ?? "")
      .toLowerCase()
      .includes(search.trim().toLowerCase())
  );

  return (
    <>
      <PageHeader
        eyebrow="Performance"
        title="The standings."
        description="Cumulative scores. Shared scores receive the same rank."
        actions={
          <button
            className="btn"
            type="button"
            disabled={loading}
            onClick={() => setReload((value) => value + 1)}
          >
            {loading ? "Refreshing…" : "Refresh standings"}
          </button>
        }
      />

      {loading ? (
        <Loading label="Loading standings" />
      ) : error ? (
        <Notice tone="error">{error}</Notice>
      ) : (
        <>
          <div className="metrics">
            <div className="metric">
              <div className="metric-label">Participants listed</div>
              <div className="metric-value mono">{rows.length}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Leading score</div>
              <div className="metric-value mono">
                {rankedRows.length
                  ? formatScore(rankedRows[0].score)
                  : "—"}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Ranking</div>
              <div className="metric-value">By score</div>
            </div>
          </div>

          <Panel
            title="Participant standings"
            aside={<span className="pill">{visibleRows.length} shown</span>}
          >
            <div className="panel-body">
              <label className="field" style={{ maxWidth: 340 }}>
                <span className="field-label">Find a participant</span>
                <input
                  type="search"
                  className="input"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by username"
                />
              </label>
            </div>

            {rows.length === 0 ? (
              <EmptyState
                title="The board is open."
                description="Scores will appear here when they become available."
              />
            ) : visibleRows.length === 0 ? (
              <EmptyState
                title="No matching participants"
                description="Try another username."
              />
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <caption className="sr-only">
                    Participant rankings by cumulative score
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Rank</th>
                      <th scope="col">Participant</th>
                      <th scope="col" className="align-right">Points</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row, index) => {
                      const name =
                        row.participant?.username ?? "Participant";

                      return (
                        <tr
                          key={
                            row.id ??
                            row.participant?.id ??
                            `${name}-${index}`
                          }
                        >
                          <td>
                            <span
                              className={`rank ${
                                row.rank === 1 ? "rank-first" : ""
                              }`}
                            >
                              {String(row.rank).padStart(2, "0")}
                            </span>
                          </td>

                          <td>
                            <div className="person">
                              <span className="avatar" aria-hidden="true">
                                {initials(name)}
                              </span>
                              <span className="person-name">{name}</span>
                            </div>
                          </td>

                          <td className="align-right">
                            <span className="score">
                              {formatScore(row.score)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </>
  );
}