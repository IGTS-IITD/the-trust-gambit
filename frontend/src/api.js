// const BASE = (() => {
//   const fromEnv = import.meta?.env?.VITE_API_BASE_URL;
//   if (fromEnv) return fromEnv.replace(/\/$/, "") + "/api";
//   return `${window.location.origin}/api`;
// })();

export const BASE = "http://localhost:8000/api";

export function getToken() {
  return localStorage.getItem("tg_token") || "";
}
export function setToken(token) {
  localStorage.setItem("tg_token", token);
}
export function clearToken() {
  localStorage.removeItem("tg_token");
  localStorage.removeItem("tg_username");
  localStorage.removeItem("tg_participant_id");
}
export function setUsername(u) {
  localStorage.setItem("tg_username", u);
}
export function getUsername() {
  return localStorage.getItem("tg_username") || "";
}
export function setParticipantId(id) {
  localStorage.setItem("tg_participant_id", String(id));
}
export function getParticipantId() {
  const v = localStorage.getItem("tg_participant_id");
  return v ? Number.parseInt(v, 10) : null;
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && getToken()) headers["Authorization"] = `Token ${getToken()}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  console.log(`${BASE}${path}`, path, { method, body }, "=>", res.status, data);

  if (!res.ok) {
    const message = (data && (data.detail || data.error)) || res.statusText;
    throw new Error(message || "Request failed");
  }
  return data;
}

/* Auth */
export const apiLogin = (username, password) =>
  request("/login/", {
    method: "POST",
    body: { username, password },
    auth: false,
  });

export const apiRegister = (payload) =>
  request("/register/", { method: "POST", body: payload, auth: false });

/* Profile */
export const apiGetProfile = () => request("/profile/");
export const apiUpdateProfileHostel = (hostel_id) =>
  request("/profile/", { method: "PATCH", body: { hostel_id } });

/* Reference Data */
export const apiGetHostels = () => request("/hostels/", { auth: false });
export const apiGetDomains = () => request("/domains/");

/* Game */
export const apiCurrentRound = () => request("/current-round/");
export const apiSubmitAction = (payload) =>
  request("/submit-action/", { method: "POST", body: payload });

export const apiLeaderboard = () => request("/leaderboard/");
export const apiRounds = () => request("/rounds/");
export const apiRoundGraph = (roundId) =>
  request(`/rounds/${roundId}/delegation-graph/`);

export const apiPostSelfRatings = (payload) =>
  request("/self-ratings/", { method: "POST", body: payload });
export const apiGetSelfRatings = () => request("/self-ratings/");
export const apiGetAllRatings = () => request("/all-ratings/");
