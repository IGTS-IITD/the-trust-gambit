import { useEffect, useRef, useState } from "react";
import {
  apiCurrentRound,
  apiSubmitAction,
  apiGetAllRatings,
} from "../api.js";
import {
  EmptyState,
  Field,
  Loading,
  Notice,
  PageHeader,
  Panel,
} from "../components/UI.jsx";

const POLL_INTERVAL_MS = 5000;

function domainLabel(domain) {
  if (domain && typeof domain === "object") {
    return domain.name ?? String(domain.id ?? "—");
  }

  return domain == null ? "—" : String(domain);
}

function domainKeys(value) {
  if (value == null) return [];

  if (typeof value === "object") {
    return [value.id, value.name]
      .filter((item) => item != null)
      .map(String);
  }

  return [String(value)];
}

function ratingMatchesRound(rating, round) {
  if (!round) return false;

  const roundKeys = new Set([
    ...domainKeys(round.domain),
    ...domainKeys(round.domain_id),
  ]);

  return [
    ...domainKeys(rating.domain),
    ...domainKeys(rating.domain_id),
  ].some((key) => roundKeys.has(key));
}

function formatTime(seconds) {
  if (seconds == null) return "—";

  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const remainder = safe % 60;

  return `${String(minutes).padStart(2, "0")}:${String(
    remainder
  ).padStart(2, "0")}`;
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [syncError, setSyncError] = useState("");
  const [reload, setReload] = useState(0);

  const [round, setRound] = useState(null);
  const [delegationTargets, setDelegationTargets] = useState([]);
  const [ratings, setRatings] = useState([]);
  const [ratingsUnavailable, setRatingsUnavailable] = useState(false);

  const [deadline, setDeadline] = useState(null);
  const [clock, setClock] = useState(Date.now());

  const [actionType, setActionType] = useState("SOLVE");
  const [submittedAnswer, setSubmittedAnswer] = useState("");
  const [delegatedTo, setDelegatedTo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submittedRoundId, setSubmittedRoundId] = useState(null);
  const [submissionError, setSubmissionError] = useState("");
  const [submissionMessage, setSubmissionMessage] = useState("");

  const currentRoundIdRef = useRef(null);
  const mountedRef = useRef(false);
  const submissionInFlightRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer;

    const poll = async () => {
      try {
        const response = await apiCurrentRound();
        if (cancelled) return;

        const nextRound = response.current_round ?? null;
        const nextRoundId = nextRound?.id ?? null;
        const previousRoundId = currentRoundIdRef.current;

        if (nextRoundId !== previousRoundId) {
          currentRoundIdRef.current = nextRoundId;

          setActionType("SOLVE");
          setSubmittedAnswer("");
          setDelegatedTo("");
          setSubmittedRoundId(null);
          setSubmissionError("");
          setSubmissionMessage("");

          if (previousRoundId !== null) {
            window.dispatchEvent(new Event("round_updated"));
          }
        }

        setRound(nextRound);
        setDelegationTargets(
          Array.isArray(response.delegation_targets)
            ? response.delegation_targets
            : []
        );

        const now = Date.now();
        const remaining = nextRound?.seconds_remaining;
        const numericRemaining = Number(remaining);

        setClock(now);
        setDeadline(
          remaining != null && Number.isFinite(numericRemaining)
            ? now + Math.max(0, numericRemaining) * 1000
            : null
        );

        setSyncError("");
      } catch (error) {
        if (!cancelled) {
          setSyncError(
            error.message || "Unable to synchronize with the game."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          timer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      }
    };

    poll();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [reload]);

  useEffect(() => {
    if (deadline === null) return;

    const timer = window.setInterval(() => {
      setClock(Date.now());
    }, 250);

    return () => window.clearInterval(timer);
  }, [deadline]);

  useEffect(() => {
    let cancelled = false;

    setRatings([]);
    setRatingsUnavailable(false);

    if (!round?.id) return;

    apiGetAllRatings()
      .then((response) => {
        if (!Array.isArray(response)) {
          throw new Error("Unexpected ratings response.");
        }

        if (!cancelled) setRatings(response);
      })
      .catch(() => {
        if (!cancelled) setRatingsUnavailable(true);
      });

    return () => {
      cancelled = true;
    };
  }, [round?.id]);

  const secondsRemaining =
    deadline === null
      ? null
      : Math.max(0, Math.ceil((deadline - clock) / 1000));

  const roundClosed =
    Boolean(round?.is_completed) || secondsRemaining === 0;

  const alreadySubmitted =
    round != null && submittedRoundId === round.id;

  const controlsDisabled =
    submitting ||
    alreadySubmitted ||
    roundClosed ||
    Boolean(syncError);

  const duration = Number(round?.duration_seconds);

  const progress =
    secondsRemaining !== null && duration > 0
      ? Math.max(0, Math.min(100, (secondsRemaining / duration) * 100))
      : null;

  const relevantRatings = ratings.filter((rating) =>
    ratingMatchesRound(rating, round)
  );

  const ratingFor = (participantId) =>
    relevantRatings.find(
      (rating) =>
        String(rating.participant?.id ?? rating.participant) ===
        String(participantId)
    )?.rating;

  const onSubmitAction = async (event) => {
    event.preventDefault();

    if (
      !round ||
      controlsDisabled ||
      submissionInFlightRef.current
    ) {
      return;
    }

    setSubmissionError("");
    setSubmissionMessage("");

    if (actionType === "SOLVE" && !submittedAnswer.trim()) {
      setSubmissionError("Enter an answer before submitting.");
      return;
    }

    if (actionType === "DELEGATE" && !delegatedTo) {
      setSubmissionError("Choose a participant to delegate to.");
      return;
    }

    const submittedForRound = round.id;
    const payload = { action_type: actionType };

    if (actionType === "SOLVE") {
      payload.submitted_answer = submittedAnswer.trim();
    }

    if (actionType === "DELEGATE") {
      payload.delegated_to = Number(delegatedTo);
    }

    submissionInFlightRef.current = true;
    setSubmitting(true);

    try {
      await apiSubmitAction(payload);

      if (
        mountedRef.current &&
        currentRoundIdRef.current === submittedForRound
      ) {
        setSubmittedRoundId(submittedForRound);
        setSubmissionMessage(
          "Decision recorded. Waiting for the round to conclude."
        );
      }
    } catch (error) {
      if (
        mountedRef.current &&
        currentRoundIdRef.current === submittedForRound
      ) {
        setSubmissionError(
          error.message || "Your decision could not be submitted."
        );
      }
    } finally {
      submissionInFlightRef.current = false;
      if (mountedRef.current) setSubmitting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Decision desk"
        title="Make your move."
        description="Assess the question. Back your judgment—or someone else's."
        actions={
          <span className="pill">
            <span className="status-dot" aria-hidden="true" />
            {syncError ? "Sync interrupted" : "Updates every 5s"}
          </span>
        }
      />

      {loading ? (
        <Loading label="Loading the current round" />
      ) : !round ? (
        <Panel>
          <EmptyState
            title={syncError ? "Game status unavailable" : "Waiting for play"}
            description={
              syncError ||
              "There is no active round available to you yet. This page checks automatically."
            }
          >
            <button
              className="btn"
              type="button"
              onClick={() => setReload((value) => value + 1)}
            >
              Check again
            </button>
          </EmptyState>
        </Panel>
      ) : (
        <div className="stack">
          {syncError && (
            <Notice tone="error">
              {syncError} Showing the last received round. Submissions
              are paused until synchronization recovers.
            </Notice>
          )}

          <div className="metrics" style={{ marginBottom: 0 }}>
            <div className="metric">
              <div className="metric-label">Round</div>
              <div className="metric-value mono">
                {String(round.round_number).padStart(2, "0")}
              </div>
            </div>

            <div className="metric">
              <div className="metric-label">Domain</div>
              <div className="metric-value">
                {domainLabel(round.domain)}
              </div>
            </div>

            <div className="metric">
              <div className="metric-label">Time remaining</div>
              <div
                className={`timer ${
                  secondsRemaining !== null && secondsRemaining <= 10
                    ? "urgent"
                    : ""
                }`}
                aria-label={
                  secondsRemaining === null
                    ? "Timer unavailable"
                    : `${secondsRemaining} seconds remaining`
                }
              >
                {formatTime(secondsRemaining)}
              </div>
            </div>
          </div>

          <div className="split-layout">
            <Panel
              title="The question"
              aside={
                <span className={`pill ${!roundClosed ? "pill-live" : ""}`}>
                  {roundClosed ? "Round closing" : "In progress"}
                </span>
              }
            >
              {progress !== null && (
                <div className="progress-track" aria-hidden="true">
                  <div
                    className={`progress-fill ${
                      secondsRemaining <= 10 ? "urgent" : ""
                    }`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}

              <div className="panel-body">
                <p className="eyebrow">Independent judgment</p>
                <div className="question">{round.question_text}</div>

                <div className="question-footer">
                  <p className="form-note">
                    Solve directly, delegate to an available participant,
                    or pass this round.
                  </p>
                </div>
              </div>
            </Panel>

            <Panel title="Your decision">
              <div className="panel-body">
                <form className="form" onSubmit={onSubmitAction}>
                  <fieldset
                    className="action-switch"
                    disabled={controlsDisabled}
                  >
                    <legend className="field-label">Choose an action</legend>

                    {[
                      ["SOLVE", "Solve"],
                      ["DELEGATE", "Delegate"],
                      ["PASS", "Pass"],
                    ].map(([value, label]) => (
                      <label className="action-choice" key={value}>
                        <input
                          type="radio"
                          name="action"
                          value={value}
                          checked={actionType === value}
                          onChange={() => setActionType(value)}
                        />
                        <span>{label}</span>
                      </label>
                    ))}
                  </fieldset>

                  {actionType === "SOLVE" && (
                    <Field label="Your answer">
                      <textarea
                        className="input"
                        rows={4}
                        value={submittedAnswer}
                        onChange={(event) =>
                          setSubmittedAnswer(event.target.value)
                        }
                        placeholder="Enter your answer"
                        disabled={controlsDisabled}
                        required
                      />
                    </Field>
                  )}

                  {actionType === "DELEGATE" && (
                    <>
                      <Field
                        label="Delegate to"
                        hint="Self-ratings reflect participants' own assessments."
                      >
                        <select
                          className="input"
                          value={delegatedTo}
                          onChange={(event) =>
                            setDelegatedTo(event.target.value)
                          }
                          disabled={controlsDisabled}
                          required
                        >
                          <option value="">Select a participant</option>
                          {delegationTargets.map((participant) => {
                            const rating = ratingFor(participant.id);

                            return (
                              <option
                                key={participant.id}
                                value={participant.id}
                              >
                                {participant.username} ·{" "}
                                {rating == null
                                  ? "Not rated"
                                  : `${rating}/10`}
                              </option>
                            );
                          })}
                        </select>
                      </Field>

                      {delegationTargets.length === 0 && (
                        <Notice>
                          No delegation targets are currently available.
                        </Notice>
                      )}

                      {ratingsUnavailable && (
                        <Notice>
                          Self-ratings could not be loaded. Available
                          participants are still listed.
                        </Notice>
                      )}
                    </>
                  )}

                  {actionType === "PASS" && (
                    <Notice>
                      You will submit a pass for this round.
                    </Notice>
                  )}

                  {roundClosed && !alreadySubmitted && (
                    <Notice>
                      The round has ended. Waiting for the next update.
                    </Notice>
                  )}

                  <Notice tone="error">{submissionError}</Notice>
                  <Notice tone="success">{submissionMessage}</Notice>

                  <button
                    type="submit"
                    className="btn btn-primary btn-block"
                    disabled={
                      controlsDisabled ||
                      (actionType === "DELEGATE" &&
                        delegationTargets.length === 0)
                    }
                  >
                    {submitting
                      ? "Submitting…"
                      : alreadySubmitted
                        ? "Decision recorded"
                        : "Submit decision"}
                  </button>

                  <p className="form-note">
                    The server determines whether a submission arrives
                    before the round closes.
                  </p>
                </form>
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}