import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  apiRegister,
  apiGetHostels,
  setToken,
  setUsername,
  setParticipantId,
} from "../api.js";

export default function Register() {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    hostel_id: "",
  });
  const [hostels, setHostels] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    apiGetHostels()
      .then(setHostels)
      .catch((err) => {
        setHostels([]);
        console.error("Failed to fetch hostels", err);
      });
  }, []);

  const onChange = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        username: form.username,
        email: form.email,
        password: form.password,
        ...(form.hostel_id
          ? { hostel_id: Number.parseInt(form.hostel_id, 10) }
          : {}),
      };
      const res = await apiRegister(payload);
      setToken(res.token);
      setUsername(res.user?.username || form.username);
      if (res.participant_id) setParticipantId(res.participant_id);
      navigate("/");
    } catch (err) {
      setError(err.message || "Registration failed");
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl p-8">
        <div className="text-center mb-6">
          <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3 border border-blue-200">
            <svg
              className="w-7 h-7 text-blue-600"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14c-3.866 0-7 2.239-7 5v1h14v-1c0-2.761-3.134-5-7-5z"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-800">
            Create your account
          </h1>
          <p className="text-slate-600 text-sm mt-1">Join The Trust Gambit</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Username
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              value={form.username}
              onChange={(e) => onChange("username", e.target.value)}
              placeholder="johndoe"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Email
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              type="email"
              value={form.email}
              onChange={(e) => onChange("email", e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Password
            </label>
            <input
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              type="password"
              value={form.password}
              onChange={(e) => onChange("password", e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Hostel (optional)
            </label>
            <select
              className="w-full px-4 py-3 border border-slate-300 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              value={form.hostel_id}
              onChange={(e) => onChange("hostel_id", e.target.value)}
            >
              <option value="">Select a hostel</option>
              {hostels.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
              {error}
            </div>
          )}

          <button
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all hover:shadow-lg active:scale-[0.98]"
            type="submit"
          >
            Create Account
          </button>
        </form>

        <div className="mt-6 text-center border-t border-slate-200 pt-6">
          <p className="text-sm text-slate-600">
            Have an account?{" "}
            <Link
              className="text-blue-600 hover:text-blue-700 font-semibold"
              to="/login"
            >
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
