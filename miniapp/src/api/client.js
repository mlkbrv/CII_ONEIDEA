/*
 * Talking to the API.
 *
 * Two credentials exist and the app prefers the cheap one. Inside Telegram it
 * sends `Authorization: tma <initData>` on every request: initData is already
 * a signed, short-lived credential, so exchanging it for a JWT before each
 * cold start would add a round trip and buy nothing. In a browser there is no
 * initData, so the app signs in once through the Telegram Login Widget and
 * carries the JWT it gets back.
 */
import { initData, isTelegram } from "../platform/telegram";

const TOKEN_KEY = "colafest.token";

let token = readToken();

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    // Private windows and locked-down browsers throw on access rather than
    // returning null. The app still works, it just forgets the session.
    return null;
  }
}

export function setToken(value) {
  token = value;
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* see readToken */
  }
}

export function hasToken() {
  return Boolean(token);
}

/** True when the app has some way to authenticate the next request. */
export function canAuthenticate() {
  return isTelegram || Boolean(token);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

function authHeader() {
  if (isTelegram) return { Authorization: `tma ${initData()}` };
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

export async function api(path, { method = "GET", body, signal } = {}) {
  const response = await fetch(path, {
    method,
    signal,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...authHeader(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    // A 401 on the JWT path means the token expired. Drop it so the app falls
    // back to the sign-in screen instead of retrying with a dead credential.
    if (response.status === 401 && !isTelegram) setToken(null);
    throw new ApiError(response.status, detailOf(payload));
  }

  return payload;
}

function detailOf(payload) {
  if (!payload) return null;
  if (typeof payload.detail === "string") return payload.detail;
  // FastAPI validation errors arrive as a list of {loc, msg, type}.
  if (Array.isArray(payload.detail)) return payload.detail[0]?.msg ?? null;
  return null;
}

/** Sign in with the raw initData Telegram gave us, and keep the JWT. */
export async function signInWithInitData() {
  const result = await api("/auth/telegram", {
    method: "POST",
    body: { init_data: initData() },
  });
  setToken(result.access_token);
  return result;
}

/** Sign in from a browser with what the Telegram Login Widget returned. */
export async function signInWithWidget(data) {
  const result = await api("/auth/telegram-login", {
    method: "POST",
    body: { data },
  });
  setToken(result.access_token);
  return result;
}
