/** How an itinerary is described: stops, layovers on the timeline, operators and flight numbers. */
import type { Flight, FlightSlice } from "@/api/client";
import { joinSpanish } from "@/lib/format";

/** Connections shorter than this are highlighted (design: "Conexión corta"). */
export const SHORT_CONNECTION_MINUTES = 60;

/** "Operado por SWISS" / "Operado por City Airlines, Lufthansa y SWISS". */
export function operatorsLabel(slice: FlightSlice): string {
  const names = [...new Set(slice.segments.map((s) => s.operating_carrier.name))];
  return `Operado por ${joinSpanish(names)}`;
}

export function stopsLabel(stops: number): string {
  if (stops === 0) return "Directo";
  return stops === 1 ? "1 escala" : `${stops} escalas`;
}

export interface StopMarker {
  airport: string;
  minutes: number | null;
  short: boolean;
  /** Position of the layover on the timeline, 0-100. */
  left: number;
  width: number;
}

/**
 * Layovers placed on the slice timeline by real time: segment and connection durations come
 * from the API, so no time zone conversion is needed.
 */
/** What `stopMarkers` needs: durations of flights and layovers (search and order slices have them). */
export interface TimedSlice {
  segments: { duration_minutes?: number | null }[];
  connections: { airport: string; duration_minutes?: number | null }[];
}

export function stopMarkers(slice: TimedSlice): StopMarker[] {
  const durations = slice.segments.map((s) => s.duration_minutes);
  const layovers = slice.connections.map((c) => c.duration_minutes);
  const known = [...durations, ...layovers].every((d) => d !== null && d !== undefined);
  const total = known ? [...durations, ...layovers].reduce<number>((a, b) => a + (b ?? 0), 0) : 0;

  let elapsed = 0;
  return slice.connections.map((connection, i) => {
    const minutes = connection.duration_minutes ?? null;
    let left: number;
    let width: number;
    if (known && total > 0) {
      elapsed += durations[i] ?? 0;
      left = (elapsed / total) * 100;
      width = ((minutes ?? 0) / total) * 100;
      elapsed += minutes ?? 0;
    } else {
      left = ((i + 1) / (slice.connections.length + 1)) * 100;
      width = 0;
    }
    return {
      airport: connection.airport,
      minutes,
      short: minutes !== null && minutes < SHORT_CONNECTION_MINUTES,
      left,
      width,
    };
  });
}

/** "LX 317 · LX 14" for every slice of a flight. */
export function flightNumbersOf(flight: Pick<Flight, "slices">): string {
  return flight.slices
    .map((s) =>
      s.segments
        .map(
          (g) =>
            `${g.marketing_carrier.code} ${/^\d+$/.test(g.flight_number) ? Number(g.flight_number) : g.flight_number}`,
        )
        .join(" · "),
    )
    .join(" / ");
}
