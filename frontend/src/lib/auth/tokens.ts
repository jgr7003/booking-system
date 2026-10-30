import { useSyncExternalStore } from "react";
import { decodeBase64urlText } from "./base64url";
import { clearMemoryStorage, deleteValue, readValue, writeValue } from "./storage";

/**
 * Tokens of the session of this device (03-usuarios-y-acceso.md §10 and §14):
 *
 * - the access token lives only in memory; after a reload a new one is asked with the refresh token;
 * - the refresh token is kept in IndexedDB, next to the device key: without the key it is useless.
 *
 * This module only keeps them; `src/api/auth.ts` talks to the API.
 */

/** Claims of the access token that the interface reads. They decide what to show, never what is allowed. */
export interface AccessClaims {
  sub: string;
  org: string | null;
  sid: string;
  exp: number;
  name: string;
  email: string;
  lang: "es" | "en" | null;
}

/** Why the session ended, for the notice on the sign-in screen. */
export type SessionEnd = "revoked" | "expired" | "signed_out";

interface State {
  accessToken: string | null;
  claims: AccessClaims | null;
  /** Whether the stored refresh token was already looked for (until then the user is «unknown»). */
  ready: boolean;
  hasRefreshToken: boolean;
  ended: SessionEnd | null;
}

const REFRESH_KEY = "refresh-token";

let state: State = { accessToken: null, claims: null, ready: false, hasRefreshToken: false, ended: null };
const listeners = new Set<() => void>();
const endListeners = new Set<(reason: SessionEnd) => void>();

function set(next: Partial<State>) {
  state = { ...state, ...next };
  for (const listener of listeners) listener();
}

/** Reads the claims of an access token without checking it (the backend checks every request). */
export function readClaims(accessToken: string): AccessClaims {
  return JSON.parse(decodeBase64urlText(accessToken.split(".")[1] ?? "")) as AccessClaims;
}

export function getAccessToken(): string | null {
  return state.accessToken;
}

export async function getRefreshToken(): Promise<string | null> {
  return (await readValue<string>(REFRESH_KEY)) ?? null;
}

/** Looks for a stored refresh token once, on start. */
export async function loadStoredSession(): Promise<void> {
  if (state.ready) return;
  set({ ready: true, hasRefreshToken: (await getRefreshToken()) !== null });
}

/** Saves the tokens of a sign in or a refresh. */
export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  await writeValue(REFRESH_KEY, refreshToken);
  set({ accessToken, claims: readClaims(accessToken), ready: true, hasRefreshToken: true, ended: null });
}

/** Forgets the session of this device (sign out, or the backend closed it). */
export async function clearSession(reason: SessionEnd): Promise<void> {
  await deleteValue(REFRESH_KEY);
  set({ accessToken: null, claims: null, ready: true, hasRefreshToken: false, ended: reason });
  for (const listener of endListeners) listener(reason);
}

/**
 * Runs when the session of this device ends, so data kept for that user in the browser (such as
 * a checkout draft) can be forgotten.
 *
 * @returns A function that stops listening.
 */
export function onSessionEnd(listener: (reason: SessionEnd) => void): () => void {
  endListeners.add(listener);
  return () => endListeners.delete(listener);
}

/** Forgets why the last session ended, once the notice was shown. */
export function acknowledgeSessionEnd(): void {
  if (state.ended) set({ ended: null });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The session state, for components. */
export function useSessionState(): State {
  return useSyncExternalStore(subscribe, () => state);
}

/** Resets everything (tests). */
export function resetSessionForTests(): void {
  clearMemoryStorage();
  state = { accessToken: null, claims: null, ready: false, hasRefreshToken: false, ended: null };
}
