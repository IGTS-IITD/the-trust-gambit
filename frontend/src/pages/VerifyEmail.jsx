import { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  apiVerifyEmail,
  setToken,
  setUsername,
  setParticipantId,
} from "../api.js";

export default function VerifyEmail() {
  const { uid, token } = useParams();
  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return; // avoid double-fire under StrictMode's dev double-invoke
    ran.current = true;

    apiVerifyEmail(uid, token)
      .then((res) => {
        setToken(res.token);
        setUsername(res.username);
        if (res.participant_id) setParticipantId(res.participant_id);
        setStatus("success");
        setTimeout(() => navigate("/"), 1500);
      })
      .catch((err) => {
        setError(err.message || "Verification failed");
        setStatus("error");
      });
  }, [uid, token, navigate]);

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl p-8 text-center">
        {status === "verifying" && (
          <>
            <div className="animate-pulse text-slate-600">
              Verifying your email...
            </div>
          </>
        )}
        {status === "success" && (
          <>
            <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-200">
              <svg
                className="w-7 h-7 text-green-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-slate-800 mb-2">
              Email verified!
            </h1>
            <p className="text-slate-600 text-sm">Taking you in...</p>
          </>
        )}
        {status === "error" && (
          <>
            <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-200">
              <svg
                className="w-7 h-7 text-red-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-slate-800 mb-2">
              Verification failed
            </h1>
            <p className="text-slate-600 text-sm mb-4">{error}</p>
            <Link
              className="text-blue-600 hover:text-blue-700 font-semibold text-sm"
              to="/login"
            >
              Back to login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
