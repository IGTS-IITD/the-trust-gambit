import {
  Outlet,
  Link,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { getToken, clearToken } from "./api.js";
import NavBar from "./components/NavBar.jsx";
import { EmptyState } from "./components/UI.jsx";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const authed = Boolean(getToken());

  const isPublicPage =
    ["/login", "/register"].includes(location.pathname) ||
    location.pathname.startsWith("/verify-email/");

  const handleLogout = () => {
    clearToken();
    navigate("/login", { replace: true });
  };

  return (
    <div className="tg-shell">
      <a href="#main-content" className="sr-only focus:not-sr-only">
        Skip to content
      </a>

      <header className="site-header">
        <div className="header-inner">
          <Link
            to="/"
            className="brand"
            aria-label="The Trust Gambit home"
          >
            <span className="brand-symbol" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
            </span>

            <span>
              <span className="brand-name">The Trust Gambit</span>
              <span className="brand-caption" style={{ display: "block" }}>
                A game of judgment
              </span>
            </span>
          </Link>

          <NavBar authed={authed} onLogout={handleLogout} />
        </div>
      </header>

      <main id="main-content" className="site-main" tabIndex={-1}>
        {!authed && !isPublicPage ? (
          <div className="panel verification">
            <EmptyState
              title="Take your seat."
              description="Sign in to join your game, submit decisions, and follow the standings."
            >
              <Link to="/login" className="btn btn-primary">
                Sign in
              </Link>
              <Link to="/register" className="btn">
                Create account
              </Link>
            </EmptyState>
          </div>
        ) : (
          <Outlet />
        )}
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <span>
            © {new Date().getFullYear()} The Trust Gambit
          </span>
          <span>STRATEGY / JUDGMENT / DELEGATION</span>
        </div>
      </footer>
    </div>
  );
}