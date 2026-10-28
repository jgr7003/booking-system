/** Calendar dates of the traveler, as "YYYY-MM-DD" text. */

/** Today in the browser's time zone (the traveler's calendar day), as "YYYY-MM-DD". */
export function todayIso(now: number | Date = Date.now()): string {
  const date = new Date(now);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
