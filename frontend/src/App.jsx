import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { getToken, clearToken } from "./api.js";
import NavBar from "./components/NavBar.jsx";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const authed = Boolean(getToken());

  const handleLogout = () => {
    clearToken();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="border-b bg-white shadow-sm sticky top-0 z-50">
        <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="font-bold text-xl text-blue-600 hover:text-blue-700 transition-colors"
          >
            🎲 The Trust Gambit
          </Link>
          <NavBar authed={authed} onLogout={handleLogout} />
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
        {/* Show a simple hint to login if trying to access protected pages */}
        {!authed && !["/login", "/register"].includes(location.pathname) ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-8 text-center max-w-md mx-auto">
            <div className="mb-6">
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
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-slate-800 mb-2">
                Authentication Required
              </h2>
              <p className="text-slate-600">
                Please sign in to access this page
              </p>
            </div>
            <div className="flex gap-3 justify-center">
              <Link
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all hover:shadow-md active:scale-95"
                to="/login"
              >
                Login
              </Link>
              <Link
                className="px-6 py-2.5 border border-slate-300 bg-white text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-all hover:shadow-sm active:scale-95"
                to="/register"
              >
                Register
              </Link>
            </div>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
      <footer className="border-t bg-white mt-auto">
        <div className="mx-auto max-w-5xl px-4 py-6 text-center">
          <p className="text-sm text-slate-600">
            © {new Date().getFullYear()} The Trust Gambit
          </p>
          <p className="text-xs text-slate-500 mt-1">
            A strategic delegation game
          </p>
        </div>
      </footer>
    </div>
  );
}
