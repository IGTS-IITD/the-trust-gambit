import { useEffect, useState } from "react";
import {
  apiGetDomains,
  apiGetProfile,
  apiGetSelfRatings,
  apiPostSelfRatings,
} from "../api.js";
import {
  EmptyState,
  Field,
  Loading,
  Notice,
  PageHeader,
  Panel,
} from "../components/UI.jsx";

function domainIdOf(domain) {
  return domain && typeof domain === "object" ? domain.id : domain;
}

export default function SelfRatings() {
  const [domains, setDomains] = useState([]);
  const [selfRatings, setSelfRatings] = useState([]);
  const [participantId, setParticipantId] = useState(null);

  const [domainId, setDomainId] = useState("");
  const [rating, setRating] = useState(5);
  const [justification, setJustification] = useState("");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [message, setMessage] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setLoadError("");

    Promise.all([
      apiGetDomains(),
      apiGetSelfRatings(),
      apiGetProfile(),
    ])
      .then(([nextDomains, nextRatings, profile]) => {
        if (
          !Array.isArray(nextDomains) ||
          !Array.isArray(nextRatings)
        ) {
          throw new Error("Unexpected ratings response.");
        }

        if (cancelled) return;

        setDomains(nextDomains);
        setSelfRatings(nextRatings);
        setParticipantId(profile.id);
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error.message || "Unable to load self-ratings.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reload]);

  const submittedDomainIds = new Set(
    selfRatings.map((item) => String(domainIdOf(item.domain)))
  );

  const availableDomains = domains.filter(
    (domain) => !submittedDomainIds.has(String(domain.id))
  );

  const getDomainName = (domain) => {
    if (domain && typeof domain === "object" && domain.name) {
      return domain.name;
    }

    const id = domainIdOf(domain);

    return (
      domains.find((item) => String(item.id) === String(id))?.name ??
      `Domain ${id}`
    );
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitError("");
    setMessage("");

    if (!participantId || !domainId) {
      setSubmitError("Choose a domain before submitting.");
      return;
    }

    if (!justification.trim()) {
      setSubmitError("Add a brief justification for your rating.");
      return;
    }

    const numericRating = Number(rating);

    if (
      !Number.isInteger(numericRating) ||
      numericRating < 0 ||
      numericRating > 10
    ) {
      setSubmitError("Enter a whole-number rating from 0 to 10.");
      return;
    }

    setSubmitting(true);

    try {
      await apiPostSelfRatings({
        participant: participantId,
        domain: Number(domainId),
        rating: numericRating,
        justification: justification.trim(),
      });

      setMessage("Self-rating recorded.");
      setDomainId("");
      setRating(5);
      setJustification("");

      try {
        const nextRatings = await apiGetSelfRatings();

        if (!Array.isArray(nextRatings)) {
          throw new Error("Unexpected ratings response.");
        }

        setSelfRatings(nextRatings);
        setLoadError("");
      } catch {
        setLoadError(
          "Your rating was saved, but the list could not be refreshed. Refresh before submitting another rating."
        );
      }
    } catch (error) {
      setSubmitError(error.message || "Unable to submit your rating.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Self-assessment"
        title="Know your strengths."
        description="Give other participants a clear view of your confidence in each domain."
        actions={
          <button
            className="btn"
            type="button"
            disabled={loading || submitting}
            onClick={() => setReload((value) => value + 1)}
          >
            Refresh
          </button>
        }
      />

      {loading ? (
        <Loading label="Loading self-ratings" />
      ) : (
        <div className="stack">
          <Notice tone="error">{loadError}</Notice>

          <div className="equal-layout">
            <Panel title="Add a self-rating">
              <div className="panel-body">
                {!loadError && availableDomains.length === 0 ? (
                  <EmptyState
                    title={
                      domains.length === 0
                        ? "No domains available"
                        : "Your assessments are complete."
                    }
                    description={
                      domains.length === 0
                        ? "Domains will appear here when they are configured."
                        : "You have submitted a rating for every available domain."
                    }
                  />
                ) : (
                  <form className="form" onSubmit={onSubmit}>
                    <Field label="Domain">
                      <select
                        className="input"
                        value={domainId}
                        onChange={(event) => {
                          setDomainId(event.target.value);
                          setMessage("");
                          setSubmitError("");
                        }}
                        disabled={submitting || Boolean(loadError)}
                        required
                      >
                        <option value="">Select a domain</option>
                        {domains.map((domain) => {
                          const alreadyRated = submittedDomainIds.has(
                            String(domain.id)
                          );

                          return (
                            <option
                              key={domain.id}
                              value={domain.id}
                              disabled={alreadyRated}
                            >
                              {domain.name}
                              {alreadyRated ? " — already rated" : ""}
                            </option>
                          );
                        })}
                      </select>
                    </Field>

                    <Field
                      label="Confidence rating"
                      hint="Use a whole number from 0 to 10."
                    >
                      <input
                        className="input mono"
                        type="number"
                        inputMode="numeric"
                        min={0}
                        max={10}
                        step={1}
                        value={rating}
                        onChange={(event) => setRating(event.target.value)}
                        disabled={submitting || Boolean(loadError)}
                        required
                      />
                    </Field>

                    <Field
                      label="Your reasoning"
                      hint={`${justification.length}/500 characters`}
                    >
                      <textarea
                        className="input"
                        rows={5}
                        maxLength={500}
                        value={justification}
                        onChange={(event) =>
                          setJustification(event.target.value)
                        }
                        placeholder="Describe the experience or knowledge behind your rating."
                        disabled={submitting || Boolean(loadError)}
                        required
                      />
                    </Field>

                    <Notice tone="error">{submitError}</Notice>

                    <button
                      className="btn btn-primary btn-block"
                      type="submit"
                      disabled={
                        submitting ||
                        !participantId ||
                        !domainId ||
                        Boolean(loadError)
                      }
                    >
                      {submitting ? "Submitting…" : "Record self-rating"}
                    </button>

                    <p className="form-note">
                      One assessment per domain. Self-ratings are visible
                      to other authenticated participants.
                    </p>
                  </form>
                )}

                {message && (
                  <div style={{ marginTop: 18 }}>
                    <Notice tone="success">{message}</Notice>
                  </div>
                )}
              </div>
            </Panel>

            <Panel
              title="Your assessments"
              aside={
                <span className="pill">{selfRatings.length} submitted</span>
              }
            >
              {selfRatings.length === 0 ? (
                <EmptyState
                  title="Start with what you know."
                  description="Your submitted assessments will appear here."
                />
              ) : (
                <ul className="record-list">
                  {selfRatings.map((item) => (
                    <li
                      key={item.id}
                      className="record"
                      style={{ alignItems: "flex-start" }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <h3 className="record-title">
                          {getDomainName(item.domain)}
                        </h3>
                        <p className="record-copy">
                          {item.justification}
                        </p>
                      </div>

                      <span className="pill" style={{ flexShrink: 0 }}>
                        {item.rating}/10
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}