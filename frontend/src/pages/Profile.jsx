import { useEffect, useState } from "react";
import {
  apiGetProfile,
  apiGetHostels,
  apiUpdateProfileHostel,
  setParticipantId,
} from "../api.js";
import {
  Field,
  Loading,
  Notice,
  PageHeader,
  Panel,
  formatScore,
  initials,
} from "../components/UI.jsx";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [hostels, setHostels] = useState([]);
  const [hostelId, setHostelId] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [message, setMessage] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setLoadError("");

    Promise.all([apiGetProfile(), apiGetHostels()])
      .then(([nextProfile, nextHostels]) => {
        if (!Array.isArray(nextHostels)) {
          throw new Error("Unexpected hostel response.");
        }

        if (cancelled) return;

        setProfile(nextProfile);
        setHostels(nextHostels);
        setHostelId(String(nextProfile.hostel?.id ?? ""));
        setParticipantId(nextProfile.id);
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error.message || "Unable to load your profile.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reload]);

  const onSave = async (event) => {
    event.preventDefault();
    if (saving) return;

    setSaving(true);
    setSaveError("");
    setMessage("");

    const requestedHostel = hostelId;
    let updateAccepted = false;

    try {
      await apiUpdateProfileHostel(
        requestedHostel === "" ? null : Number(requestedHostel)
      );

      updateAccepted = true;

      // Read back the authoritative state rather than pretending
      // the requested change was applied.
      const nextProfile = await apiGetProfile();

      setProfile(nextProfile);
      setHostelId(String(nextProfile.hostel?.id ?? ""));
      setParticipantId(nextProfile.id);

      if (String(nextProfile.hostel?.id ?? "") !== requestedHostel) {
        setSaveError(
          "The server did not apply the selected hostel. Your current saved profile is shown."
        );
      } else {
        setMessage("Profile updated.");
      }
    } catch (error) {
      setSaveError(
        updateAccepted
          ? "The update was accepted, but the saved profile could not be refreshed. Reload before making another change."
          : error.message || "Unable to update your profile."
      );
    } finally {
      setSaving(false);
    }
  };

  const dirty =
    profile !== null &&
    hostelId !== String(profile.hostel?.id ?? "");

  return (
    <div className="narrow">
      <PageHeader
        eyebrow="Participant account"
        title="Your profile."
        description="Account details and your current hostel affiliation."
        actions={
          <button
            className="btn"
            type="button"
            disabled={loading || saving}
            onClick={() => setReload((value) => value + 1)}
          >
            Refresh
          </button>
        }
      />

      {loading ? (
        <Loading label="Loading your profile" />
      ) : loadError ? (
        <Notice tone="error">{loadError}</Notice>
      ) : profile ? (
        <div className="stack">
          <Panel
            title="Participant record"
            aside={<span className="pill">ID {profile.id}</span>}
          >
            <div className="panel-body">
              <div className="person" style={{ marginBottom: 28 }}>
                <span
                  className="avatar"
                  style={{ width: 48, height: 48, fontSize: 14 }}
                  aria-hidden="true"
                >
                  {initials(profile.user?.username)}
                </span>

                <div>
                  <div
                    className="person-name"
                    style={{ fontSize: 18 }}
                  >
                    {profile.user?.username ?? "Participant"}
                  </div>
                  <div className="small muted">
                    {profile.hostel?.name ?? "No hostel selected"}
                  </div>
                </div>
              </div>

              <dl className="identity-grid">
                <div>
                  <dt className="metric-label">Username</dt>
                  <dd className="identity-value">
                    {profile.user?.username ?? "—"}
                  </dd>
                </div>

                <div>
                  <dt className="metric-label">Email</dt>
                  <dd className="identity-value">
                    {profile.user?.email || "—"}
                  </dd>
                </div>

                <div>
                  <dt className="metric-label">Participant ID</dt>
                  <dd className="identity-value mono">{profile.id}</dd>
                </div>

                <div>
                  <dt className="metric-label">Total score</dt>
                  <dd className="identity-value mono">
                    {profile.total_score == null
                      ? "—"
                      : `${formatScore(profile.total_score)} pts`}
                  </dd>
                </div>
              </dl>

              <p className="form-note">
                Your username and email are shown as recorded by the server.
              </p>
            </div>
          </Panel>

          <Panel title="Hostel affiliation">
            <div className="panel-body">
              <form className="form" onSubmit={onSave}>
                <Field
                  label="Hostel"
                  hint="Choose a hostel, or select none to request removal of your affiliation."
                >
                  <select
                    className="input"
                    value={hostelId}
                    disabled={saving}
                    onChange={(event) => {
                      setHostelId(event.target.value);
                      setMessage("");
                      setSaveError("");
                    }}
                  >
                    <option value="">None</option>
                    {hostels.map((hostel) => (
                      <option key={hostel.id} value={hostel.id}>
                        {hostel.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Notice tone="success">{message}</Notice>
                <Notice tone="error">{saveError}</Notice>

                <div className="button-row">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!dirty || saving}
                  >
                    {saving ? "Saving…" : "Save changes"}
                  </button>

                  {dirty && !saving && (
                    <span className="small muted">Unsaved changes</span>
                  )}
                </div>
              </form>
            </div>
          </Panel>
        </div>
      ) : (
        <Notice>No participant profile is available.</Notice>
      )}
    </div>
  );
}