import type { FlightSegment, FlightSlice } from "@/api/client";
import { PlaneIcon } from "@/components/icons";
import { cn } from "@/lib/cn";
import { dayOffset, formatDuration, formatTime } from "@/lib/format";
import { operatorsLabel, stopMarkers, stopsLabel } from "./logic";

/** "LX 317": marketing carrier and flight number, without leading zeros. */
export function flightNumber(segment: FlightSegment): string {
  const number = /^\d+$/.test(segment.flight_number) ? Number(segment.flight_number) : segment.flight_number;
  return `${segment.marketing_carrier.code} ${number}`;
}

/** "LX 317 · LX 14": marketing flight numbers of a slice. */
export function flightNumbers(slice: FlightSlice): string {
  return slice.segments.map(flightNumber).join(" · ");
}

/**
 * Departure, the dashed line with each layover placed by real time, and arrival (design).
 *
 * Desktop: stops and duration above the line, operator below. Mobile: both in one line below.
 */
export function SliceTimeline({ slice, label }: { slice: FlightSlice; label?: string }) {
  const first = slice.segments[0];
  const last = slice.segments.at(-1);
  if (!first || !last) return null;
  const markers = stopMarkers(slice);
  const days = dayOffset(first.departing_at, last.arriving_at);
  const stops = (
    <span className={cn("font-semibold", slice.stops === 0 ? "text-ok" : "text-ink")}>
      {stopsLabel(slice.stops)}
    </span>
  );

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <span className="text-[11px] font-semibold tracking-[0.06em] text-muted uppercase">{label}</span>
      )}
      <div className="grid grid-cols-[52px_minmax(0,1fr)_52px] items-center gap-2.5 sm:grid-cols-[76px_minmax(0,1fr)_76px] sm:gap-[18px]">
        <span className="flex flex-col">
          <span className="data text-[18px] font-semibold sm:text-[22px]">
            {formatTime(first.departing_at)}
          </span>
          <span className="text-[12px] sm:text-[14px]">{slice.origin.code}</span>
        </span>

        <span className="flex min-w-0 flex-col items-center gap-1.5">
          <span className="flex items-center gap-2.5 text-[13px] max-sm:hidden">
            {stops}
            <span aria-hidden className="h-[13px] w-px bg-subtle" />
            <span className="data text-muted">{formatDuration(slice.duration_minutes)}</span>
          </span>
          <span className="relative block h-[34px] w-full sm:h-9">
            <span
              aria-hidden
              className="absolute inset-x-0 top-[21px] border-t-2 border-dashed border-ink-2"
            />
            {markers.length === 0 && (
              <span className="absolute top-[13px] left-1/2 -ml-2.5 flex w-5 justify-center bg-white sm:top-[11px] sm:-ml-3 sm:h-[22px] sm:w-6 sm:items-center">
                <PlaneIcon size={18} className="text-ink sm:h-5 sm:w-5" />
              </span>
            )}
            {markers.map((m) => (
              <span
                key={`${m.airport}-${m.left}`}
                className="absolute top-0 flex -translate-x-1/2 flex-col items-center gap-px"
                style={{ left: `${(m.left + m.width / 2).toFixed(1)}%` }}
                title={`Conexión en ${m.airport} · ${formatDuration(m.minutes)}`}
              >
                <span
                  className={cn(
                    "data text-[11px] leading-[14px] font-semibold sm:text-[12px]",
                    m.short ? "text-short" : "text-ink",
                  )}
                >
                  {m.airport}
                </span>
                <span
                  className={cn(
                    "box-border h-[13px] w-[13px] rounded-full border-[3px] bg-white sm:h-3.5 sm:w-3.5",
                    m.short ? "border-short" : "border-ink",
                  )}
                />
              </span>
            ))}
          </span>
          <span className="text-center text-[13px] text-ink-2 max-sm:hidden">{operatorsLabel(slice)}</span>
        </span>

        <span className="flex flex-col items-end">
          <span className="data text-[18px] font-semibold sm:text-[22px]">
            {formatTime(last.arriving_at)}
            {days !== 0 && (
              <sup
                className="ml-0.5 text-[11px] text-warn"
                title={`Llega ${days > 0 ? `${days} día(s) después` : "el día anterior"}`}
              >
                {days > 0 ? `+${days}` : days}
              </sup>
            )}
          </span>
          <span className="text-[12px] sm:text-[14px]">{slice.destination.code}</span>
        </span>
      </div>
      <span className="text-center text-[12px] text-ink-2 sm:hidden">
        {stops} · {formatDuration(slice.duration_minutes)} · {operatorsLabel(slice)}
      </span>
    </div>
  );
}
