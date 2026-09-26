import { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  apiVerifyEmail,
  setToken,
  setUsername,
  setParticipantId,
} from "../api.js";
import {
  EmptyState,
  Loading,
  Notice,
} from "../components/UI.jsx";

export default function VerifyEmail() {
  const { uid, token } = useParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState("verifying");
  const [error, setError] = useState("");

  const requestRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let redirectTimer;

    setStatus("verifying");
    setError("");

    const key = JSON.stringify([uid, token]);

    if (!requestRef.current || requestRef.current.key !== key) {
      requestRef.current = {
        key,
        promise: Promise.resolve().then(() =>
          apiVerifyEmail(uid, token)
        ),
      };
    }

    requestRef.current.promise
      .then((response) => {
        if (cancelled) return;

        setToken(response.token);
        setUsername(response.username);

        if (response.participant_id != null) {
          setParticipantId(response.participant_id);
        }

        setStatus("success");

        redirectTimer = window.setTimeout(() => {
          navigate("/", { replace: true });
        }, 1500);
      })
      .catch((err) => {
        if (cancelled) return;

        setError(err.message || "This verification link could not be used.");
        setStatus("error");
      });

    return () => {
      cancelled = true;
      window.clearTimeout(redirectTimer);
    };
  }, [uid, token, navigate]);

  return (
    <div className="verification">
      {status === "verifying" && (
        <>
          <div style={{ marginBottom: 22 }}>
            <p className="eyebrow">Account verification</p>
            <h1 className="page-title">Checking your link.</h1>
            <p className="page-description">
              Please wait while we verify your email address.
            </p>
          </div>

          <Loading label="Verifying your email address" />
        </>
      )}

      {status === "success" && (
        <div className="panel">
          <EmptyState
            title="You're verified."
            description="Your account is ready. Taking you to the game."
          >
            <Link className="btn btn-primary" to="/">
              Continue now
            </Link>
          </EmptyState>
        </div>
      )}

      {status === "error" && (
        <div className="panel">
          <EmptyState
            title="We couldn't verify that link."
            description="It may have expired or already been used."
          >
            <Link className="btn btn-primary" to="/login">
              Return to sign in
            </Link>
          </EmptyState>

          <div className="panel-body" style={{ paddingTop: 0 }}>
            <Notice tone="error">{error}</Notice>
          </div>
        </div>
      )}
    </div>
  );
}