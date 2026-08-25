"use client";
import { useState } from "react";
import { Link } from "react-router-dom";

const linkClass =
  "px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium";

export default function NavBar({ authed, onLogout }) {
  const [open, setOpen] = useState(false);

  const authedLinks = (
    <>
      <Link to="/" className={linkClass} onClick={() => setOpen(false)}>
        Dashboard
      </Link>
      <Link
        to="/leaderboard"
        className={linkClass}
        onClick={() => setOpen(false)}
      >
        Leaderboard
      </Link>
      <Link to="/rounds" className={linkClass} onClick={() => setOpen(false)}>
        Rounds
      </Link>
      <Link
        to="/self-ratings"
        className={linkClass}
        onClick={() => setOpen(false)}
      >
        Self Ratings
      </Link>
      <Link
        to="/profile"
        className={linkClass}
        onClick={() => setOpen(false)}
      >
        Profile
      </Link>
      <button
        className="md:ml-2 px-4 py-2 border border-slate-300 bg-white text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-all hover:shadow-sm active:scale-95 text-left"
        onClick={() => {
          setOpen(false);
          onLogout();
        }}
      >
        Logout
      </button>
    </>
  );

  const guestLinks = (
    <>
      <Link
        to="/login"
        className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all hover:shadow-md active:scale-95 text-center"
        onClick={() => setOpen(false)}
      >
        Login
      </Link>
      <Link
        to="/register"
        className="px-5 py-2 border border-slate-300 bg-white text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-all hover:shadow-sm active:scale-95 text-center"
        onClick={() => setOpen(false)}
      >
        Register
      </Link>
    </>
  );

  return (
    <nav className="text-sm">
      {/* Desktop nav */}
      <div className="hidden md:flex items-center gap-2">
        {authed ? authedLinks : guestLinks}
      </div>

      {/* Mobile hamburger toggle */}
      <button
        className="md:hidden w-11 h-11 grid place-items-center rounded-lg border border-slate-300 bg-white text-slate-700 active:scale-95 transition-all"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {open ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          )}
        </svg>
      </button>

      {/* Mobile dropdown panel */}
      {open && (
        <div className="md:hidden absolute left-0 right-0 top-full bg-white border-b border-slate-200 shadow-lg px-4 py-3 flex flex-col gap-1 z-50">
          {authed ? authedLinks : guestLinks}
        </div>
      )}
    </nav>
  );
}
