import { memo, type ReactNode } from "react";
import type { Flight } from "@/api/client";
import { AirlineBadge } from "@/components/flight/AirlineBadge";
import { SliceTimeline } from "@/components/flight/SliceTimeline";
import { CarryOnIcon, CheckedBagIcon } from "@/components/icons";
import type { Cell } from "@/lib/cell";
import { cn } from "@/lib/cn";
import { bagCell, fareCarryOn, fareCheckedBags, fareName } from "@/lib/flights/fares";
import { flightNumbersOf } from "@/lib/flights/itinerary";
import { formatMoney } from "@/lib/format";
import type { FlightInsight } from "./logic";

const TAG_TONES = {
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  info: "bg-action-soft text-action-hover",
  neutral: "bg-canvas text-ink-2",
} as const;

/** "Mano"/"Valija" of the cheapest fare: green if included, struck if not, plain if unknown. */
function BagChip({ cell, label, icon }: { cell: Cell; label: string; icon: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-[5px] text-[12px] font-semibold sm:text-[13px]",
        cell.tone === "ok" && "text-ok",
        cell.tone === "bad" && "text-subtle line-through",
        cell.tone === "na" && "text-muted",
      )}
      title={`${label}: ${cell.label}`}
    >
      <span className="max-sm:hidden">{icon}</span>
      {label}
      {cell.tone === "na" && <span className="font-normal">?</span>}
    </span>
  );
}

interface FlightCardProps {
  flight: Flight;
  /** Tag and note, computed once for the whole list (see `flightInsights`). */
  insight: FlightInsight | undefined;
  /** Stable callback that receives the flight key, so unchanged cards don't re-render. */
  onSelect: (key: string) => void;
  /** Whether selecting opens a dialog (fares) or moves to another step (outbound → returns). */
  opensDialog?: boolean;
  /** Caption above the price, e.g. "Ida y vuelta desde". Defaults to "Desde". */
  priceCaption?: string;
  /** Call to action under the price, e.g. "17 vueltas". Defaults to the number of fares. */
  actionLabel?: string;
  /** Labels of the slices shown, e.g. ["Vuelta"]. Defaults to "Ida"/"Vuelta" on round trips. */
  sliceLabels?: string[];
}

/**
 * One flight (design board "Resultados"). Its fares open in a modal (`FaresDialog`).
 *
 * Memoized and without open/closed state: opening the fares doesn't re-render any card.
 */
export const FlightCard = memo(function FlightCard({
  flight,
  insight,
  onSelect,
  opensDialog = true,
  priceCaption = "Desde",
  actionLabel,
  sliceLabels,
}: FlightCardProps) {
  const tag = insight?.tag ?? null;
  const cheapest = flight.fares[0];
  if (!cheapest) return null;
  const checked = bagCell(fareCheckedBags(cheapest), "checked");
  const carryOn = bagCell(fareCarryOn(cheapest), "carry_on");
  const roundTrip = flight.slices.length > 1;
  const faresLabel =
    actionLabel ?? (flight.fares.length > 1 ? `${flight.fares.length} tarifas` : fareName(cheapest));

  return (
    <article id={`flight-${flight.key}`} className="relative rounded-lg border border-line bg-white">
      {tag && (
        <span
          className={cn(
            "absolute -top-[11px] right-5 rounded px-2.5 py-[3px] text-[12px] font-semibold",
            TAG_TONES[tag.tone],
          )}
        >
          {tag.label}
        </span>
      )}
      <button
        type="button"
        onClick={() => onSelect(flight.key)}
        aria-haspopup={opensDialog ? "dialog" : undefined}
        className="grid w-full cursor-pointer text-left sm:grid-cols-[minmax(0,1fr)_260px] sm:items-stretch"
      >
        <span className="flex flex-col gap-1 px-3.5 pt-2.5 pb-2 sm:px-6 sm:pt-3.5 sm:pb-4">
          <span className="flex items-center gap-2 text-[12px] text-muted sm:text-[13px]">
            <span className="max-sm:hidden">
              <AirlineBadge code={flight.owner.code} />
            </span>
            {flight.owner.name} · <span className="data">{flightNumbersOf(flight)}</span>
          </span>
          {flight.slices.map((slice, i) => (
            <SliceTimeline
              key={`${slice.origin.code}-${slice.destination.code}`}
              slice={slice}
              label={sliceLabels?.[i] ?? (roundTrip ? (i === 0 ? "Ida" : "Vuelta") : undefined)}
            />
          ))}
        </span>

        <span className="flex items-center justify-between gap-1 border-t border-dashed border-line-dash px-3.5 py-2 sm:flex-col sm:items-start sm:justify-center sm:border-t-0 sm:border-l sm:px-6 sm:py-3.5">
          <span className="flex gap-2.5 sm:gap-3">
            <span className="sr-only">
              Tarifa más barata: equipaje de mano {carryOn.label.toLowerCase()}, valija{" "}
              {checked.label.toLowerCase()}.
            </span>
            <span aria-hidden className="flex gap-2.5 sm:gap-3">
              <BagChip cell={carryOn} label="Mano" icon={<CarryOnIcon />} />
              <BagChip cell={checked} label="Valija" icon={<CheckedBagIcon />} />
            </span>
          </span>
          <span className="flex items-baseline gap-1 sm:flex-col sm:items-start sm:gap-1">
            <span className="text-[12px] text-muted sm:text-[13px]">{priceCaption}</span>
            <span className="data text-[16px] font-semibold sm:text-[20px]">
              {formatMoney(flight.lowest_price)}
            </span>
            <span className={cn("text-[13px] font-semibold text-action", opensDialog && "max-sm:hidden")}>
              {faresLabel} {opensDialog ? "▾" : "→"}
            </span>
          </span>
        </span>
      </button>
    </article>
  );
});
