import type { ReactNode } from "react";
import type { Fare } from "@/api/client";
import type { TripItem } from "@/features/trip/public";
import { fareName } from "@/lib/flights/fares";
import { flightNumbersOf, stopsLabel } from "@/lib/flights/itinerary";
import { formatAmount, formatDate, formatDuration, formatTime, joinSpanish } from "@/lib/format";
import { bagsSummary } from "./logic";

/** "Tu vuelo" (design board "Pasajeros y pago"): itinerary, fare, price breakdown and the action. */
export function FlightSummary({ item, children }: { item: TripItem; children: ReactNode }) {
  const { flight, fare } = item;
  const operators = [
    ...new Set(flight.slices.flatMap((s) => s.segments.map((g) => g.operating_carrier.name))),
  ];

  return (
    <aside
      aria-label="Resumen"
      className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-3 rounded-lg border border-line bg-white p-[18px] text-[14px] max-sm:max-w-none"
    >
      <span className="text-[12px] font-semibold tracking-[0.06em] text-muted uppercase">Tu vuelo</span>
      {flight.slices.map((slice) => {
        const first = slice.segments[0];
        const last = slice.segments.at(-1);
        const stops = slice.connections.map((c) => c.airport);
        return (
          <div key={`${slice.origin.code}-${slice.destination.code}`} className="flex flex-col gap-1">
            <span className="font-mono text-[16px] font-semibold">
              {slice.origin.code} {first && formatTime(first.departing_at)} → {slice.destination.code}{" "}
              {last && formatTime(last.arriving_at)}
            </span>
            <span className="text-ink-2">
              {first && formatDate(first.departing_at)} · {formatDuration(slice.duration_minutes)} ·{" "}
              {stopsLabel(slice.stops)}
              {stops.length > 0 && ` ${stops.join(", ")}`}
            </span>
          </div>
        );
      })}
      <span className="text-ink-2">
        {flightNumbersOf(flight)} · operado por {joinSpanish(operators)}
      </span>
      <span className="text-ink-2">
        {fareName(fare)} · {bagsSummary(fare)}
      </span>
      <PriceBreakdown fare={fare} />
      {children}
    </aside>
  );
}

function PriceBreakdown({ fare }: { fare: Fare }) {
  const { base, taxes, total } = fare.price;
  return (
    <div className="flex flex-col gap-1.5 border-t border-line-soft pt-3">
      {base && (
        <div className="flex justify-between">
          <span>Tarifa base</span>
          <span className="font-mono">{formatAmount(base)}</span>
        </div>
      )}
      {taxes && (
        <div className="flex justify-between">
          <span>Impuestos y cargos</span>
          <span className="font-mono">{formatAmount(taxes)}</span>
        </div>
      )}
      <div className="mt-1 flex items-baseline justify-between">
        <strong>Total</strong>
        <span className="font-mono text-[22px] font-semibold">
          {formatAmount(total)} <span className="text-[13px]">{total.currency}</span>
        </span>
      </div>
    </div>
  );
}
