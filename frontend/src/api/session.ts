import type { Middleware } from "openapi-fetch";
import { createDpopProof } from "@/lib/auth/dpop";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  readClaims,
  type SessionEnd,
  saveTokens,
} from "@/lib/auth/tokens";

/**
 * Authentication of every request to the API (03-usuarios-y-acceso.md §11 and §14):
 *
 * - each request carries a DPoP proof signed by the device key, and the access token as
 *   `Authorization: DPoP <token>` when there is a session;
 * - an access token about to expire (or missing after a reload) is renewed first;
 * - a `401 token_expired` is renewed and retried once;
 * - if the backend closed the session (`session_revoked`, `token_binding_mismatch`...), it's
 *   forgotten here and the interface sends the person to sign in.
 */

const REFRESH_PATH = "/api/v1/auth/token/refresh";

// Renew the access token this many seconds before it expires, so no request travels with a stale one.
const RENEW_BEFORE_S = 30;

// Requests waiting for a retry keep a copy of their body here (a Request body can be read only once).
const originals = new WeakMap<Request, Request>();

let refreshing: Promise<string | null> | null = null;

/** Why the backend ended the session, from the code of its `401`. */
function endReason(code: string): SessionEnd | null {
  if (code === "session_expired") return "expired";
  if (code === "session_revoked" || code === "token_binding_mismatch" || code === "invalid_token")
    return "revoked";
  return null;
}

async function errorCode(response: Response): Promise<string> {
  try {
    const body = (await response.clone().json()) as { error?: { code?: string } };
    return body.error?.code ?? "";
  } catch {
    return "";
  }
}

async function requestRefresh(): Promise<string | null> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return null;
  const url = `${window.location.origin}${REFRESH_PATH}`;
  const response = await globalThis.fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", DPoP: await createDpopProof("POST", url) },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (response.ok) {
    const tokens = (await response.json()) as { access_token: string; refresh_token: string };
    await saveTokens(tokens.access_token, tokens.refresh_token);
    return tokens.access_token;
  }
  const reason = endReason(await errorCode(response));
  if (reason) await clearSession(reason);
  return null;
}

/**
 * Exchanges the refresh token for a new pair, once at a time.
 *
 * Refresh tokens are single-use: if two tabs refreshed with the same one at once, the backend
 * would take it as stolen and close the session. Web Locks serialize the tabs; inside one tab,
 * concurrent callers share the same refresh.
 */
export function refreshSession(): Promise<string | null> {
  refreshing ??= (async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.locks) {
        return await navigator.locks.request("vuelos-refresh", requestRefresh);
      }
      return await requestRefresh();
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

/** A valid access token: the current one, or a new one if it's missing or about to expire. */
export async function freshAccessToken(): Promise<string | null> {
  const token = getAccessToken();
  if (token && readClaims(token).exp - RENEW_BEFORE_S > Date.now() / 1000) return token;
  if (!(await getRefreshToken())) return null;
  return refreshSession();
}

async function sign(request: Request, accessToken: string | null): Promise<Request> {
  const signed = new Request(request);
  signed.headers.set("DPoP", await createDpopProof(signed.method, signed.url, accessToken ?? undefined));
  if (accessToken) signed.headers.set("Authorization", `DPoP ${accessToken}`);
  return signed;
}

/** `fetch` signed like the API client does, for what openapi-fetch can't do (the SSE stream). */
export async function authorizedFetch(url: string, init?: RequestInit): Promise<Response> {
  return globalThis.fetch(await sign(new Request(url, init), await freshAccessToken()));
}

export const authMiddleware: Middleware = {
  async onRequest({ request }) {
    if (new URL(request.url).pathname === REFRESH_PATH) return undefined;
    const signed = await sign(request, await freshAccessToken());
    originals.set(signed, signed.clone());
    return signed;
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || !request.headers.has("Authorization")) return undefined;
    const code = await errorCode(response);
    if (code === "token_expired") {
      const original = originals.get(request);
      const token = await refreshSession();
      if (!original || !token) return undefined;
      return globalThis.fetch(await sign(original, token));
    }
    const reason = endReason(code);
    if (reason) await clearSession(reason);
    return undefined;
  },
};
