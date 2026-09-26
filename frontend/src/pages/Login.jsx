import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  apiLogin,
  apiResendVerification,
  setToken,
  setUsername,
} from "../api.js";
import {
  AuthLayout,
  Field,
  Notice,
} from "../components/UI.jsx";

export default function Login() {
  const navigate = useNavigate();

  const [username, setUsernameInput] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [unverified, setUnverified] = useState(false);
  const [resendEmail, setResendEmail] = useState("");
  const [resending, setResending] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [resendError, setResendError] = useState("");

  const onSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;

    setLoading(true);
    setError("");
    setUnverified(false);
    setResendMessage("");
    setResendError("");

    try {
      const response = await apiLogin(username.trim(), password);

      setToken(response.token);
      setUsername(response.username);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign in.");
      setUnverified(Boolean(err.data?.unverified));
    } finally {
      setLoading(false);
    }
  };

  const onResend = async (event) => {
    event.preventDefault();
    if (resending) return;

    setResending(true);
    setResendMessage("");
    setResendError("");

    try {
      const response = await apiResendVerification(resendEmail.trim());
      setResendMessage(response.detail);
    } catch (err) {
      setResendError(err.message || "Unable to resend verification.");
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Participant access"
      title={<>Good judgment.<br />Better company.</>}
      description="Return to your game. Review the field, make your decision, and see where trust takes you."
    >
      <div style={{ marginBottom: 26 }}>
        <h2 className="panel-title" style={{ fontSize: 20 }}>Sign in</h2>
        <p className="form-note" style={{ marginTop: 8 }}>
          Use your participant account to continue.
        </p>
      </div>

      <form className="form" onSubmit={onSubmit}>
        <Field label="Username">
          <input
            className="input"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            value={username}
            onChange={(event) => setUsernameInput(event.target.value)}
            placeholder="Your username"
            required
          />
        </Field>

        <Field label="Password">
          <input
            className="input"
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Your password"
            required
          />
        </Field>

        <Notice tone="error">{error}</Notice>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={loading}
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {unverified && (
        <div className="auth-bottom">
          <form className="form" onSubmit={onResend}>
            <p className="form-note">
              Need another verification link?
            </p>

            <Field label="Account email">
              <input
                className="input"
                type="email"
                autoComplete="email"
                value={resendEmail}
                onChange={(event) => setResendEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </Field>

            <Notice tone="success">{resendMessage}</Notice>
            <Notice tone="error">{resendError}</Notice>

            <button
              className="btn"
              type="submit"
              disabled={resending}
            >
              {resending ? "Sending…" : "Resend verification"}
            </button>
          </form>
        </div>
      )}

      <div className="auth-bottom">
        New to the game?{" "}
        <Link className="text-link" to="/register">
          Create an account
        </Link>
      </div>
    </AuthLayout>
  );
}