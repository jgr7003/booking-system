import type { Flight, FlightSegment, FlightSlice } from "@/api/client";
import { flightNumber } from "@/components/flight/SliceTimeline";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import { SHORT_CONNECTION_MINUTES } from "@/lib/flights/itinerary";
import { dayOffset, formatDate, formatDuration, formatTime } from "@/lib/format";
import { amenityRows } from "./logic";
import { SECTION, SECTION_TITLE } from "./styles";

export function Itinerary({ flight }: { flight: Flight }) {
  return (
    <section aria-labelledby="itinerary" className={SECTION}>
      <h2 id="itinerary" className={SECTION_TITLE}>
        Itinerario{" "}
        <span className="text-[13px] font-normal text-muted">
          · horarios en hora local de cada aeropuerto
        </span>
      </h2>
      {flight.slices.map((slice, i) => (
        <SliceItinerary
          key={`${slice.origin.code}-${slice.destination.code}`}
          slice={slice}
          title={
            flight.slices.length > 1
              ? `${i === 0 ? "Ida" : "Vuelta"} · ${formatDate(slice.segments[0]?.departing_at ?? "")}`
              : undefined
          }
        />
      ))}
    </section>
  );
}

function SliceItinerary({ slice, title }: { slice: FlightSlice; title?: string }) {
  return (
    <>
      {title && (
        <h3 className="field-label border-b border-line-soft bg-surface-2 px-[18px] py-2">{title}</h3>
      )}
      {slice.segments.map((segment, i) => {
        const connection = slice.connections[i];
        const next = slice.segments[i + 1];
        const short = (connection?.duration_minutes ?? Number.POSITIVE_INFINITY) < SHORT_CONNECTION_MINUTES;
        const terminalsUnknown = !segment.destination.terminal && !next?.origin.terminal;
        return (
          <div key={`${segment.marketing_carrier.code}${segment.flight_number}`}>
            <SegmentRow segment={segment} />
            {connection && next && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line-soft bg-surface-2 px-[18px] py-2.5 text-[13px] sm:pl-[146px]">
                <span
                  className={cn(
                    "data rounded border px-2 py-[3px] font-semibold",
                    short ? "border-[#C27A00] bg-warn-soft text-warn" : "border-line bg-white",
                  )}
                >
                  Conexión en {connection.airport} · {formatDuration(connection.duration_minutes)}
                  {short && " · corta"}
                </span>
                <span className="text-ink-2">
                  {formatTime(segment.arriving_at)} → {formatTime(next.departing_at)} · cambio de avión
                  {terminalsUnknown ? " · terminal sin dato en ambos tramos" : ""}
                </span>
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

function SegmentRow({ segment }: { segment: FlightSegment }) {
  const days = dayOffset(segment.departing_at, segment.arriving_at);
  const place = (p: FlightSegment["origin"]) => (
    <span className="text-[14px]">
      <strong>{p.code}</strong> · {p.name} ·{" "}
      {p.terminal ? `Terminal ${p.terminal}` : <span className="text-muted italic">Terminal sin dato</span>}
    </span>
  );

  return (
    <div className="grid gap-3 border-b border-line-soft px-[18px] py-4 sm:grid-cols-[110px_minmax(0,1fr)_minmax(0,260px)] sm:gap-[18px]">
      <div className="flex gap-3 sm:flex-col sm:gap-1">
        <span className="data text-[15px] font-semibold">{flightNumber(segment)}</span>
        <span className="text-[13px] text-muted">{formatDuration(segment.duration_minutes)}</span>
      </div>
      <div className="flex flex-col gap-2.5">
        <div className="flex items-baseline gap-3">
          <span className="data w-14 shrink-0 text-[18px] font-semibold">
            {formatTime(segment.departing_at)}
          </span>
          {place(segment.origin)}
        </div>
        <div className="flex items-baseline gap-3">
          <span className="data w-14 shrink-0 text-[18px] font-semibold">
            {formatTime(segment.arriving_at)}
            {days > 0 && <sup className="text-[11px] text-warn">+{days}</sup>}
          </span>
          {place(segment.destination)}
        </div>
        <p className="text-[13px] text-ink-2">
          Operado por <strong>{segment.operating_carrier.name}</strong>
          {segment.aircraft ? ` · ${segment.aircraft}` : " · avión sin dato"}
          {segment.cabin?.cabin_name ? ` · Cabina ${segment.cabin.cabin_name}` : ""}
        </p>
      </div>
      <ul className="flex flex-col gap-1.5 text-[13px]">
        {amenityRows(segment).map(({ k, cell }) => (
          <li key={k} className="flex justify-between gap-2 border-b border-dotted border-line pb-1">
            <span className="text-muted">{k}</span>
            <span className={toneTextClass(cell.tone)}>{cell.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
