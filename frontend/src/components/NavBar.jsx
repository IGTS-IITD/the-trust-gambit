import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { apiGetProfile } from "../api.js";
import { formatScore } from "./UI.jsx";

const links = [
  ["/", "Play"],
  ["/leaderboard", "Standings"],
  ["/rounds", "Rounds"],
  ["/self-ratings", "Self ratings"],
  ["/profile", "Profile"],
];

export default function NavBar({ authed, onLogout }) {
  const [open, setOpen] = useState(false);
  const [score, setScore] = useState(null);
  const toggleRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;

    const handleKey = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  useEffect(() => {
    let cancelled = false;
    let requestNumber = 0;

    const fetchScore = async () => {
      const currentRequest = ++requestNumber;

      if (!authed) {
        setScore(null);
        return;
      }

      try {
        const profile = await apiGetProfile();
        if (!cancelled && currentRequest === requestNumber) {
          setScore(profile.total_score ?? 0);
        }
      } catch {
        if (!cancelled && currentRequest === requestNumber) {
          setScore(null);
        }
      }
    };

    fetchScore();
    window.addEventListener("round_updated", fetchScore);

    return () => {
      cancelled = true;
      window.removeEventListener("round_updated", fetchScore);
    };
  }, [authed, location.pathname]);

  const linkClass = ({ isActive }) =>
    `nav-link${isActive ? " active" : ""}`;

  return (
    <nav aria-label="Main navigation">
      <button
        ref={toggleRef}
        type="button"
        className="nav-toggle"
        aria-expanded={open}
        aria-controls="main-navigation"
        onClick={() => setOpen((value) => !value)}
      >
        {open ? "Close" : "Menu"}
      </button>

      <div
        id="main-navigation"
        className={`nav-links${open ? " is-open" : ""}`}
      >
        {authed ? (
          <>
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={linkClass}
                onClick={() => setOpen(false)}
              >
                {label}
              </NavLink>
            ))}

            {score !== null && (
              <span className="nav-score">
                {formatScore(score)} pts
              </span>
            )}

            <button
              type="button"
              className="nav-link nav-logout"
              onClick={() => {
                setOpen(false);
                onLogout();
              }}
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <NavLink to="/login" className={linkClass}>
              Sign in
            </NavLink>
            <NavLink to="/register" className={linkClass}>
              Register
            </NavLink>
          </>
        )}
      </div>
    </nav>
  );
}