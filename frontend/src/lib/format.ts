import type { Money } from "@/api/client";

/** Locale of numbers and dates: "6.146,64", "mar 15 dic". */
export const LOCALE = "es-AR";

const amountFormat = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "USD 402,74". Amounts are shown in their own currency, never converted. */
export function formatMoney(money: Money): string {
  return `${money.currency} ${formatAmount(money)}`;
}

/** "402,74". */
export function formatAmount(money: Money): string {
  return amountFormat.format(Number(money.amount));
}

const penaltyFormat = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 0, maximumFractionDigits: 2 });

/** Penalty as the design shows it: "300 GBP", "150,50 GBP" (amount first, no ",00"). */
export function formatPenalty(money: Money): string {
  return `${penaltyFormat.format(Number(money.amount))} ${money.currency}`;
}

/** True for "0", "0.00"... */
export function isZero(money: Money): boolean {
  return Number(money.amount) === 0;
}

/** 760 → "12 h 40 min"; 780 → "13 h"; 55 → "55 min". */
export function formatDuration(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return "Sin dato";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

/**
 * "09:00" from a local flight time ("2026-12-15T09:00:00").
 *
 * Flight times are local to their airport and have no time zone, so they're read as text:
 * converting them with `Date` would shift them to the browser's zone.
 */
export function formatTime(localDateTime: string): string {
  return localDateTime.slice(11, 16);
}

/** Calendar days between two local date-times: 1 for an arrival the next day. */
export function dayOffset(fromLocal: string, toLocal: string): number {
  const from = Date.UTC(...ymd(fromLocal));
  const to = Date.UTC(...ymd(toLocal));
  return Math.round((to - from) / 86_400_000);
}

const weekdayFormat = new Intl.DateTimeFormat(LOCALE, { weekday: "short", timeZone: "UTC" });
const longWeekdayFormat = new Intl.DateTimeFormat(LOCALE, { weekday: "long", timeZone: "UTC" });
const monthFormat = new Intl.DateTimeFormat(LOCALE, { month: "short", timeZone: "UTC" });

/** "2026-12-15" (or a local date-time) → "mar 15 dic 2026". */
export function formatDate(isoDate: string, { year = true, longWeekday = false } = {}): string {
  const date = new Date(Date.UTC(...ymd(isoDate)));
  const weekday = (longWeekday ? longWeekdayFormat : weekdayFormat).format(date).replace(".", "");
  const month = monthFormat.format(date).replace(".", "");
  const parts = [`${weekday}${longWeekday ? "," : ""}`, String(date.getUTCDate()), month];
  if (year) parts.push(String(date.getUTCFullYear()));
  return parts.join(" ");
}

/** "2026-12-15" → "15 dic". */
export function formatShortDate(isoDate: string): string {
  const date = new Date(Date.UTC(...ymd(isoDate)));
  return `${date.getUTCDate()} ${monthFormat.format(date).replace(".", "")}`;
}

/** Remaining time of an offer: "24 min", "45 s". */
export function formatRemaining(ms: number): string {
  if (ms <= 0) return "vencido";
  const minutes = Math.floor(ms / 60_000);
  return minutes >= 1 ? `${minutes} min` : `${Math.ceil(ms / 1000)} s`;
}

/** "1 adulto", "2 adultos · 1 menor". */
export function formatPassengers(adults: number, children: number): string {
  const parts = [`${adults} ${adults === 1 ? "adulto" : "adultos"}`];
  if (children > 0) parts.push(`${children} ${children === 1 ? "menor" : "menores"}`);
  return parts.join(" · ");
}

function ymd(value: string): [number, number, number] {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return [y ?? 1970, (m ?? 1) - 1, d ?? 1];
}
