import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRegister, apiGetHostels } from "../api.js";
import {
  AuthLayout,
  EmptyState,
  Field,
  Notice,
} from "../components/UI.jsx";

export default function Register() {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    hostel_id: "",
  });

  const [hostels, setHostels] = useState([]);
  const [hostelsLoading, setHostelsLoading] = useState(true);
  const [hostelsError, setHostelsError] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState("");

  useEffect(() => {
    let cancelled = false;

    apiGetHostels()
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error("Unexpected hostel response.");
        }

        if (!cancelled) setHostels(data);
      })
      .catch(() => {
        if (!cancelled) {
          setHostelsError(
            "Hostels could not be loaded. You can register without one."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setHostelsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError("");

    const email = form.email.trim();

    try {
      await apiRegister({
        username: form.username.trim(),
        email,
        password: form.password,
        ...(form.hostel_id
          ? { hostel_id: Number(form.hostel_id) }
          : {}),
      });

      setSubmittedEmail(email);
      setForm((current) => ({ ...current, password: "" }));
    } catch (err) {
      setError(err.message || "Unable to create your account.");
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedEmail) {
    return (
      <div className="panel verification">
        <EmptyState
          title="Check your inbox."
          description={`A verification link has been requested for ${submittedEmail}. Open the link to activate your account.`}
        >
          <Link className="btn btn-primary" to="/login">
            Continue to sign in
          </Link>
        </EmptyState>

        <div className="panel-body" style={{ paddingTop: 0 }}>
          <p className="form-note" style={{ textAlign: "center" }}>
            If the message does not arrive, check your spam folder.
          </p>
        </div>
      </div>
    );
  }

  return (
    <AuthLayout
      eyebrow="Join the field"
      title={<>Every decision<br />starts somewhere.</>}
      description="Create your participant account. A sharp answer matters. Knowing whom to trust matters too."
    >
      <div style={{ marginBottom: 26 }}>
        <h2 className="panel-title" style={{ fontSize: 20 }}>
          Create account
        </h2>
        <p className="form-note" style={{ marginTop: 8 }}>
          Verify your email before entering the game.
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
            value={form.username}
            onChange={(event) => update("username", event.target.value)}
            placeholder="Choose a username"
            disabled={submitting}
            required
          />
        </Field>

        <Field label="Email address">
          <input
            className="input"
            type="email"
            name="email"
            autoComplete="email"
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
            placeholder="you@example.com"
            disabled={submitting}
            required
          />
        </Field>

        <Field label="Password">
          <input
            className="input"
            type="password"
            name="password"
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
            placeholder="Create a password"
            disabled={submitting}
            required
          />
        </Field>

        <Field
          label="Hostel"
          hint="Optional. You can update this in your profile later."
        >
          <select
            className="input"
            value={form.hostel_id}
            onChange={(event) => update("hostel_id", event.target.value)}
            disabled={submitting || hostelsLoading || Boolean(hostelsError)}
          >
            <option value="">
              {hostelsLoading ? "Loading hostels…" : "No hostel selected"}
            </option>
            {hostels.map((hostel) => (
              <option key={hostel.id} value={hostel.id}>
                {hostel.name}
              </option>
            ))}
          </select>
        </Field>

        <Notice>{hostelsError}</Notice>
        <Notice tone="error">{error}</Notice>

        <button
          className="btn btn-primary btn-block"
          type="submit"
          disabled={submitting}
        >
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>

      <div className="auth-bottom">
        Already registered?{" "}
        <Link className="text-link" to="/login">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
}