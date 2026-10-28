import type { Flight } from "@/api/client";
import { stopsLabel } from "@/lib/flights/itinerary";
import { formatDate, formatDuration, formatTime, joinSpanish } from "@/lib/format";

export function FlightHeading({ flight }: { flight: Flight }) {
  const first = flight.slices[0];
  const firstSegment = first?.segments[0];
  const lastSegment = first?.segments.at(-1);
  if (!first || !firstSegment || !lastSegment) return null;
  const operators = [
    ...new Set(flight.slices.flatMap((s) => s.segments.map((g) => g.operating_carrier.name))),
  ];
  const connections = first.connections.map((c) => c.airport);
  const cityOf = (code: string) =>
    first.segments.find((s) => s.destination.code === code)?.destination.city ?? code;

  return (
    <>
      <h1 className="data text-[20px] font-bold sm:text-[28px]">
        {first.origin.code} {formatTime(firstSegment.departing_at)} → {first.destination.code}{" "}
        {formatTime(lastSegment.arriving_at)}
      </h1>
      <p className="text-[13px] text-ink-2 sm:text-[15px]">
        {formatDate(firstSegment.departing_at)} · {formatDuration(first.duration_minutes)} ·{" "}
        {stopsLabel(first.stops)}
        {connections.length > 0 && ` en ${joinSpanish(connections.map(cityOf))}`} · Vende{" "}
        <strong>{flight.owner.name}</strong>
        {operators.some((o) => o !== flight.owner.name) && (
          <>
            {" "}
            · Opera <strong>{joinSpanish(operators)}</strong>
          </>
        )}
      </p>
    </>
  );
}
