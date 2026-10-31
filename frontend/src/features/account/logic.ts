/** Rules of the list of connected devices. */
import { LOCALE } from "@/lib/format";

/** What kind of device a session name describes, for its icon. */
export function deviceKind(name: string): "computer" | "phone" | "app" {
  if (/^app\b/i.test(name)) return "app";
  if (/iphone|ipad|android/i.test(name)) return "phone";
  return "computer";
}

/** «12 oct 2026». */
export function signedInOn(iso: string): string {
  return new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(iso))
    .replace(/\./g, "")
    .replace(/ de /g, " ");
}

/** «Ahora», «Hace 5 min», «Hace 3 h» or the date. */
export function lastUse(iso: string, current: boolean, now: number = Date.now()): string {
  if (current) return "Ahora";
  const minutes = Math.floor((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 2) return "Ahora";
  if (minutes < 60) return `Hace ${minutes} min`;
  if (minutes < 24 * 60) return `Hace ${Math.floor(minutes / 60)} h`;
  return signedInOn(iso);
}
