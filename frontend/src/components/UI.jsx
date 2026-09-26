export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {description && (
          <p className="page-description">{description}</p>
        )}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Panel({ title, aside, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="panel-head">
          <h2 className="panel-title">{title}</h2>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="form-note">{hint}</span>}
    </label>
  );
}

export function Notice({ children, tone = "info" }) {
  if (!children) return null;

  return (
    <div
      className={`notice notice-${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

export function Loading({ label = "Loading data" }) {
  return (
    <div className="panel" role="status" aria-label={label}>
      <div className="loading-block" aria-hidden="true">
        <div className="skeleton" />
        <div className="skeleton" />
        <div className="skeleton" />
      </div>
    </div>
  );
}

export function EmptyState({ title, description, children }) {
  return (
    <div className="empty-state">
      <div className="empty-mark" aria-hidden="true">—</div>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {children && <div className="button-row">{children}</div>}
    </div>
  );
}

export function AuthLayout({ eyebrow, title, description, children }) {
  return (
    <div className="auth-layout">
      <section className="auth-editorial">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="auth-heading">{title}</h1>
        <p className="auth-description">{description}</p>
        <div className="auth-rule" />
        <p className="auth-footnote">
          THE TRUST GAMBIT
          <br />
          STRATEGY · JUDGMENT · DELEGATION
        </p>
      </section>
      <div className="panel auth-panel">
        <div className="panel-body">{children}</div>
      </div>
    </div>
  );
}

export function formatScore(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(number);
}

export function initials(name = "") {
  return String(name).trim().slice(0, 2).toUpperCase() || "—";
}