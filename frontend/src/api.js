// Keep the browser page and session-cookie host aligned. `localhost` and
// `127.0.0.1` are different cookie sites when SameSite=Lax is enabled.
const pageHost = typeof window !== "undefined" ? window.location.hostname : "localhost";
const defaultApiHost = pageHost === "127.0.0.1" ? "127.0.0.1" : "localhost";
const BASE = import.meta.env.VITE_API_URL || `http://${defaultApiHost}:8000`;
let csrf = null;

// Diagnostics are intentionally metadata-only. Never log request bodies,
// cookies, CSRF values, authorization headers, or response tokens.
const DEBUG_AUTH = import.meta.env.DEV || import.meta.env.VITE_AUTH_DEBUG === "true";
const logRequest = (method, path, status, detail) => {
  if (!DEBUG_AUTH && status < 400) return;
  const payload = { method, path, status };
  if (detail) payload.detail = detail;
  (status >= 400 ? console.warn : console.info)("[SmartCart API]", payload);
};

export const setCsrf = (t) => {
  csrf = t;
};

async function request(method, path, { params, body } = {}) {
  const qs = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const url = `${BASE}${path}${qs.toString() ? "?" + qs : ""}`;
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrf) headers["X-CSRF-Token"] = csrf;
  let res;
  try {
    res = await fetch(url, { method, headers, credentials: "include", body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    logRequest(method, path, 0, "network_error");
    const err = new Error("The server is not reachable");
    err.status = 0;
    throw err;
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  logRequest(method, path, res.status, res.ok ? undefined : messageOf(data, res.status));
  if (!res.ok) {
    const err = new Error(messageOf(data, res.status));
    err.status = res.status;
    err.fields = fieldErrors(data);
    if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("auth:expired"));
    throw err;
  }
  return data;
}

function messageOf(data, status) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) return d.map((e) => e.msg).join(". ");
  if (status === 404) return "Not found";
  if (status === 403) return "You do not have access to this";
  if (status === 429) return "Too many requests, try again in a moment";
  return `Request failed (${status})`;
}

function fieldErrors(data) {
  const out = {};
  const d = data && data.detail;
  if (Array.isArray(d)) d.forEach((e) => { const f = e.loc && e.loc[e.loc.length - 1]; if (f) out[f] = e.msg; });
  return out;
}

export const get = (path, params) => request("GET", path, { params });
export const post = (path, body) => request("POST", path, { body: body === undefined ? {} : body });
export const put = (path, body) => request("PUT", path, { body });
export const del = (path) => request("DELETE", path);

export const money = (v, cur = "USD") => new Intl.NumberFormat("en-US", { style: "currency", currency: cur }).format(v);
export const pct = (v) => `${(v * 100).toFixed(1)}%`;
export const when = (ms) => (ms ? new Date(ms).toLocaleString() : "-");
