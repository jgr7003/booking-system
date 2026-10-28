import type { OrderSlice } from "@/api/client";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import { stopMarkers } from "@/lib/flights/itinerary";
import { formatDate, formatDuration, formatTime } from "@/lib/format";
import { bagsLine, cityOf, daysLater, sliceBags, sliceDate, terminalLabel } from "./logic";
import { CARD } from "./styles";

export function SliceCard({ slice, label }: { slice: OrderSlice; label: "IDA" | "VUELTA" }) {
  const first = slice.segments[0];
  const last = slice.segments.at(-1);
  if (!first || !last) return null;
  const direct = slice.segments.length === 1;
  const later = daysLater(first.departing_at, last.arriving_at);
  const stops = slice.stops === 0 ? "Directo" : slice.stops === 1 ? "1 escala" : `${slice.stops} escalas`;
  const bags = bagsLine(sliceBags(slice));
  const cabin = first.passengers[0]?.cabin_name ?? "Cabina sin dato";
  const flight = `${first.marketing_carrier.code} ${first.flight_number}`;

  return (
    <article
      aria-label={label === "IDA" ? "Vuelo de ida" : "Vuelo de vuelta"}
      className={`${CARD} overflow-hidden`}
    >
      <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2 border-b border-line-soft bg-surface-2 px-5 py-2.5 max-sm:gap-2 max-sm:px-3.5">
        <span className="rounded bg-action px-2 py-[3px] font-mono text-[11px] font-semibold tracking-[0.06em] text-white sm:text-[12px]">
          {label}
        </span>
        <strong className="text-[14px] sm:text-[15px]">{formatDate(sliceDate(slice))}</strong>
        <span className="text-[14px] text-ink-2 max-sm:hidden">
          {cityOf(slice.origin)} → {cityOf(slice.destination)}
          {!direct && (
            <>
              {" "}
              · {stops} · <span className="font-mono">{formatDuration(slice.duration_minutes)}</span>
            </>
          )}
        </span>
        <span className="ml-auto text-[12px] text-muted sm:text-[13px]">
          <span className="max-sm:hidden">Tarifa </span>
          <strong className="font-normal sm:font-semibold sm:text-ink">{slice.fare_brand ?? "Tarifa"}</strong>
        </span>
      </div>

      <div className="grid grid-cols-[64px_minmax(0,1fr)_64px] items-center gap-2.5 px-3.5 py-3 sm:grid-cols-[96px_minmax(0,1fr)_96px] sm:gap-[18px] sm:px-5 sm:pt-3.5 sm:pb-4">
        <span className="flex flex-col">
          <span className="font-mono text-[20px] font-semibold sm:text-[22px]">
            {formatTime(first.departing_at)}
          </span>
          <span className="text-[13px] sm:text-[14px]">
            <strong>{slice.origin.code}</strong> · <Terminal value={first.origin.terminal} long={direct} />
          </span>
        </span>
        <Timeline slice={slice} stops={stops} />
        <span className="flex flex-col items-end">
          <span className="font-mono text-[20px] font-semibold sm:text-[22px]">
            {formatTime(last.arriving_at)}
            {later > 0 && <sup className="ml-0.5 text-[12px] text-warn">+{later}</sup>}
          </span>
          <span className="text-[13px] sm:text-[14px]">
            <strong>{slice.destination.code}</strong> ·{" "}
            <Terminal value={last.destination.terminal} long={direct} />
          </span>
        </span>
      </div>

      {direct ? (
        <>
          <div className="flex flex-wrap gap-x-5 gap-y-1.5 border-t border-dashed border-line px-5 pt-2.5 pb-3 text-[13px] text-ink-2 max-sm:hidden">
            <span>
              <span className="font-mono font-semibold text-ink">{flight}</span> · Operado por{" "}
              <strong className="text-ink">{first.operating_carrier.name}</strong>
            </span>
            <span>
              {first.aircraft ?? "Avión: sin dato"} · {cabin}
            </span>
            <span className={cn("font-semibold", toneTextClass(bags.tone))}>{bags.text}</span>
          </div>
          <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-2.5 gap-y-1.5 border-t border-dashed border-line px-3.5 py-2.5 text-[13px] sm:hidden">
            <dt className="text-muted">Vuelo</dt>
            <dd className="font-mono font-semibold">{flight}</dd>
            <dt className="text-muted">Operado por</dt>
            <dd className="font-semibold">{first.operating_carrier.name}</dd>
            <dt className="text-muted">Avión</dt>
            <dd>{first.aircraft ?? "Sin dato"}</dd>
            <dt className="text-muted">Cabina</dt>
            <dd>{cabin}</dd>
            <dt className="text-muted">Equipaje</dt>
            <dd className={cn("font-semibold", toneTextClass(bags.tone))}>
              {bags.text.replace("Equipaje: ", "")}
            </dd>
          </dl>
        </>
      ) : (
        <ol className="flex flex-col px-3.5 pt-2 pb-[18px] sm:px-5">
          {slice.segments.map((segment, i) => (
            <SegmentRow
              key={`${segment.marketing_carrier.code}${segment.flight_number}`}
              slice={slice}
              index={i}
            />
          ))}
        </ol>
      )}
    </article>
  );
}

/** "Terminal 2" on desktop for direct flights (design), "T2" on mobile and with layovers. */
function Terminal({ value, long }: { value: string | null | undefined; long: boolean }) {
  if (!long) return <>{terminalLabel(value, true)}</>;
  return (
    <>
      <span className="sm:hidden">{terminalLabel(value, true)}</span>
      <span className="max-sm:hidden">{terminalLabel(value)}</span>
    </>
  );
}

/** Line between departure and arrival: the plane for a direct flight, a dot per layover otherwise. */
function Timeline({ slice, stops }: { slice: OrderSlice; stops: string }) {
  const direct = slice.segments.length === 1;
  if (direct) {
    return (
      <span className="flex flex-col items-center gap-1.5">
        <span className="flex items-center gap-2.5 text-[12px] sm:text-[13px]">
          <span className="font-semibold text-ok">{stops}</span>
          <span className="h-[13px] w-px bg-subtle" />
          <span className="font-mono text-muted">{formatDuration(slice.duration_minutes)}</span>
        </span>
        <span className="relative block h-[22px] w-full">
          <span className="absolute inset-x-0 top-2.5 border-t-2 border-dashed border-ink-2" />
          <span className="absolute top-0 left-1/2 -ml-3 flex h-[22px] w-6 items-center justify-center bg-white">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#111827" aria-hidden="true">
              <path
                d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"
                transform="rotate(90 12 12)"
              />
            </svg>
          </span>
        </span>
      </span>
    );
  }
  return (
    <span className="relative block h-9">
      <span className="absolute inset-x-0 top-[21px] border-t-2 border-dashed border-ink-2" />
      {stopMarkers(slice).map((m) => (
        <span
          key={m.airport}
          style={{ left: `${m.left}%` }}
          className="absolute top-0 flex -translate-x-1/2 flex-col items-center gap-px"
        >
          <span
            className={cn(
              "font-mono text-[12px] leading-[14px] font-semibold",
              m.short ? "text-short" : "text-ink",
            )}
          >
            {m.airport}
          </span>
          <span
            className={cn(
              "h-3.5 w-3.5 rounded-full border-[3px] bg-white",
              m.short ? "border-short" : "border-ink",
            )}
          />
        </span>
      ))}
    </span>
  );
}

/** One flight of a slice with layovers, and the connection after it (design: state 2). */
function SegmentRow({ slice, index }: { slice: OrderSlice; index: number }) {
  const segment = slice.segments[index];
  if (!segment) return null;
  const next = slice.segments[index + 1];
  const connection = next ? slice.connections[index] : undefined;
  const short = connection?.duration_minutes != null && connection.duration_minutes < 60;
  const passenger = segment.passengers[0];
  const bags = bagsLine({
    carryOn: passenger?.baggage.carry_on ?? null,
    checked: passenger?.baggage.checked ?? null,
  });
  const place = (p: typeof segment.origin) =>
    `${p.code} · ${p.city ?? p.name} · ${terminalLabel(p.terminal, true)}`;

  return (
    <li className="flex flex-col">
      <div
        className={cn(
          "grid gap-1.5 py-3 sm:grid-cols-[110px_minmax(0,1fr)_280px] sm:gap-[18px]",
          index === 0 && "border-t border-line-soft",
        )}
      >
        <span className="flex flex-col gap-0.5">
          <span className="font-mono font-semibold">
            {segment.marketing_carrier.code} {segment.flight_number}
          </span>
          <span className="text-[13px] text-muted">{formatDuration(segment.duration_minutes)}</span>
        </span>
        <span className="flex flex-col gap-1 text-[14px]">
          <span>
            <strong className="font-mono">{formatTime(segment.departing_at)}</strong> {place(segment.origin)}{" "}
            → <strong className="font-mono">{formatTime(segment.arriving_at)}</strong>{" "}
            {place(segment.destination)}
          </span>
          <span className="text-ink-2">
            Operado por <strong className="text-ink">{segment.operating_carrier.name}</strong> ·{" "}
            {segment.aircraft ?? "Avión: sin dato"} · {passenger?.cabin_name ?? "Cabina sin dato"}
          </span>
        </span>
        <span className={cn("text-[13px] font-semibold", toneTextClass(bags.tone))}>{bags.text}</span>
      </div>
      {connection && next && (
        <div
          className={cn(
            "my-0.5 flex items-center gap-3 rounded-md border px-3.5 py-2.5 text-[14px]",
            short
              ? "border-warn-line bg-warn-soft text-warn-ink"
              : "border-line-soft bg-surface-2 text-ink-2",
          )}
        >
          <span>
            <strong>
              {short ? "Conexión corta" : "Conexión"} en {segment.destination.city ?? connection.airport} (
              {connection.airport}) ·{" "}
              <span className="font-mono">{formatDuration(connection.duration_minutes)}</span>.
            </strong>
            {short &&
              ` Cambiás de avión: buscá la puerta de ${next.marketing_carrier.code} ${next.flight_number} apenas aterrices.`}
          </span>
        </div>
      )}
    </li>
  );
}
