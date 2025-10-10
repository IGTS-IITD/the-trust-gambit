"use client";
import { Link } from "react-router-dom";

export default function NavBar({ authed, onLogout }) {
  return (
    <nav className="flex items-center gap-2 text-sm">
      {authed ? (
        <>
          <Link
            to="/"
            className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium"
          >
            Dashboard
          </Link>
          <Link
            to="/leaderboard"
            className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium"
          >
            Leaderboard
          </Link>
          <Link
            to="/rounds"
            className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium"
          >
            Rounds
          </Link>
          <Link
            to="/self-ratings"
            className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium"
          >
            Self Ratings
          </Link>
          <Link
            to="/profile"
            className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-blue-600 transition-all font-medium"
          >
            Profile
          </Link>
          <button
            className="ml-2 px-4 py-2 border border-slate-300 bg-white text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-all hover:shadow-sm active:scale-95"
            onClick={onLogout}
          >
            Logout
          </button>
        </>
      ) : (
        <>
          <Link
            to="/login"
            className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all hover:shadow-md active:scale-95"
          >
            Login
          </Link>
          <Link
            to="/register"
            className="px-5 py-2 border border-slate-300 bg-white text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-all hover:shadow-sm active:scale-95"
          >
            Register
          </Link>
        </>
      )}
    </nav>
  );
}
