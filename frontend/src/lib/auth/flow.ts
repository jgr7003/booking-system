/**
 * Small pieces of the sign-in flow that several screens share: where to go back, the provider
 * sign in in progress and the notice after creating an account with a provider.
 * They live in `sessionStorage`: they only matter to this tab, for a few minutes.
 */

const PENDING_PREFIX = "auth:oidc:";
const NOTICE_KEY = "auth:notice";
const RETURN_KEY = "auth:return-to";

/** Only a path of this app is a valid place to go back to (never another site: open redirect). */
export function safeReturnTo(value: unknown): string | null {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return null;
  }
  // The sign-in screens themselves are never a destination.
  if (/^\/(login|signup|auth\/callback)(\/|$|\?)/.test(value)) return null;
  return value;
}

/** Whether the sign in comes from the checkout (the screen then shows the trip and «Ingresa para reservar»). */
export function comesFromCheckout(returnTo: string | null): boolean {
  return returnTo?.startsWith("/checkout/") ?? false;
}

/** The trip item of a checkout path, e.g. `/checkout/duffel:abc` → `duffel:abc`. */
export function checkoutItemKey(returnTo: string | null): string | null {
  const match = returnTo?.match(/^\/checkout\/([^/?#]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export interface PendingProviderSignIn {
  provider: string;
  providerName: string;
  returnTo: string | null;
}

/** Remembers which provider a `state` belongs to, before sending the browser there. */
export function rememberProviderSignIn(authorizationUrl: string, pending: PendingProviderSignIn): void {
  const state = new URL(authorizationUrl).searchParams.get("state");
  if (state) sessionStorage.setItem(PENDING_PREFIX + state, JSON.stringify(pending));
}

/** The provider sign in of a `state`, read once (a replayed callback finds nothing). */
export function takeProviderSignIn(state: string): PendingProviderSignIn | null {
  const raw = sessionStorage.getItem(PENDING_PREFIX + state);
  sessionStorage.removeItem(PENDING_PREFIX + state);
  return raw ? (JSON.parse(raw) as PendingProviderSignIn) : null;
}

/** Shows «Te enviamos un correo para que crees una contraseña…» on the next screen. */
export function noticePasswordEmail(providerName: string): void {
  sessionStorage.setItem(NOTICE_KEY, providerName);
}

/** The provider of the pending notice, if any. */
export function pendingNotice(): string | null {
  return sessionStorage.getItem(NOTICE_KEY);
}

export function dismissNotice(): void {
  sessionStorage.removeItem(NOTICE_KEY);
}

/** Where to go after verifying the email of a new account (the link opens in another tab). */
export function rememberReturnTo(returnTo: string | null): void {
  if (returnTo) localStorage.setItem(RETURN_KEY, returnTo);
  else localStorage.removeItem(RETURN_KEY);
}

export function takeReturnTo(): string | null {
  const value = safeReturnTo(localStorage.getItem(RETURN_KEY));
  localStorage.removeItem(RETURN_KEY);
  return value;
}

/** Seconds to wait before each new resend of a verification email: it grows (60 s, 120 s, …). */
export function resendWait(resends: number): number {
  return 60 * 2 ** Math.min(resends, 3);
}

/** Initials for the avatar of the account menu, e.g. «Pepe Perez» → «PP». */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return letters.map((w) => (w ?? "").charAt(0).toUpperCase()).join("") || "?";
}

/** First name, for the account button («Pepe»). */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}
