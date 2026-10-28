/** Expiry of an offer: the rule every countdown follows (design: "pasa a ámbar a los 5 min"). */
import { useNow } from "@/lib/useNow";

/** Countdowns turn amber when less than this is left (design: "pasa a ámbar a los 5 min"). */
export const EXPIRY_WARNING_MS = 5 * 60_000;

export interface Expiry {
  /** Milliseconds left; zero or less once expired. */
  remaining: number;
  expired: boolean;
  /** Less than `EXPIRY_WARNING_MS` left (also true once expired). */
  warning: boolean;
}

/** Expiry at a given time. A missing date counts as expired. */
export function expiryOf(expiresAt: string | undefined, now: number): Expiry {
  const remaining = new Date(expiresAt ?? 0).getTime() - now;
  return { remaining, expired: remaining <= 0, warning: remaining < EXPIRY_WARNING_MS };
}

/** Expiry that updates every second, for countdowns. */
export function useExpiry(expiresAt: string | undefined): Expiry {
  return expiryOf(expiresAt, useNow(1000));
}
