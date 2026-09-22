import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiLogin, apiResendVerification, setToken, setUsername } from "../api.js";

export default function Login() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [unverified, setUnverified] = useState(false);
  const [resendEmail, setResendEmail] = useState("");
  const [resendStatus, setResendStatus] = useState("");
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setUnverified(false);
    setLoading(true);
    try {
      const res = await apiLogin(username, password);
      setToken(res.token);
      setUsername(res.username);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
      setUnverified(Boolean(err.data?.unverified));
    } finally {
      setLoading(false);
    }
  };

  const onResend = async (e) => {
    e.preventDefault();
    setResendStatus("");
    try {
      const res = await apiResendVerification(resendEmail);
      setResendStatus(res.detail);
    } catch (err) {
      setResendStatus(err.message || "Failed to resend");
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-800">Welcome Back</h1>
          <p className="text-slate-600 mt-2">
            Sign in to continue to The Trust Gambit
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Username
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
              value={username}
              onChange={(e) => setU(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Password
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all outline-none"
              type="password"
              value={password}
              onChange={(e) => setP(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}
          {unverified && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
              <p className="text-sm text-amber-800">
                Didn't get the email? Resend it below.
              </p>
              <div className="flex gap-2">
                <input
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-amber-500"
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="Your email"
                />
                <button
                  type="button"
                  onClick={onResend}
                  className="px-3 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-all whitespace-nowrap"
                >
                  Resend
                </button>
              </div>
              {resendStatus && (
                <p className="text-xs text-amber-700">{resendStatus}</p>
              )}
            </div>
          )}
          <button
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-lg active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            type="submit"
            disabled={loading}
          >
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 text-center border-t border-slate-200 pt-6">
          <p className="text-sm text-slate-600">
            Don't have an account?{" "}
            <Link
              className="text-blue-600 hover:text-blue-700 font-semibold"
              to="/register"
            >
              Create one now
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
