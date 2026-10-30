import { Link } from "@tanstack/react-router";
import { AirlineBadge } from "@/components/flight/AirlineBadge";
import { SliceTimeline } from "@/components/flight/SliceTimeline";
import { ClockIcon, LogoIcon, TrashIcon } from "@/components/icons";
import { toneTextClass } from "@/components/ui/tone";
import type { Cell } from "@/lib/cell";
import { cn } from "@/lib/cn";
import { bagCell, fareCarryOn, fareCheckedBags, fareName } from "@/lib/flights/fares";
import { flightNumbersOf } from "@/lib/flights/itinerary";
import { pickSearch } from "@/lib/flights/search";
import { formatDate, formatMoney, formatRemaining } from "@/lib/format";
import { useExpiry } from "@/lib/useExpiry";
import { conditionsLine } from "./logic";
import { type TripItem, useTrip } from "./store";
import { useRefreshTripItem } from "./useRefreshTripItem";

const ACTION = "inline-flex h-[38px] items-center gap-1.5 rounded-md border px-3.5 text-[14px] font-semibold";

/** Short summary of what a fare includes, colored like the design ("✓ Mano ✓ Maleta"). */
function bagMark(cell: Cell, label: string) {
  const mark = cell.tone === "ok" ? "✓" : cell.tone === "bad" ? "✗" : "?";
  return (
    <span className={toneTextClass(cell.tone)} title={`${label}: ${cell.label}`}>
      {mark} {label}
    </span>
  );
}

export function TripItemCard({
  item,
  position,
  onRemoved,
}: {
  item: TripItem;
  position: number;
  onRemoved: (removed: { item: TripItem; index: number }) => void;
}) {
  const remove = useTrip((s) => s.remove);
  const { refresh, refreshing } = useRefreshTripItem(item);
  const { remaining, expired, warning } = useExpiry(item.fare.expires_at);
  const { flight, fare, search } = item;
  const conditions = conditionsLine(item);

  return (
    <article
      aria-label={`Vuelo ${position}`}
      className={cn(
        "overflow-hidden rounded-lg border bg-white",
        expired ? "border-warn-line" : "border-line",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line-soft bg-surface-2 px-3.5 py-2 sm:px-5 sm:py-2.5">
        <h2 className="inline-flex items-center gap-2.5 text-[13px] font-semibold sm:text-[14px]">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-action-soft text-action max-sm:hidden">
            <LogoIcon width={16} height={16} />
          </span>
          Vuelo {position} · {flight.slices.length > 1 ? "Ida y vuelta" : "Ida"} ·{" "}
          {formatDate(search.depart, { longWeekday: true }).replace(",", "")}
        </h2>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[12px] font-semibold",
            expired ? "bg-bad-soft text-bad" : warning ? "bg-warn-soft text-warn" : "bg-canvas text-ink-2",
          )}
        >
          <ClockIcon width={13} height={13} />
          {expired ? "Precio vencido" : `Precio válido ${formatRemaining(remaining)}`}
        </span>
      </div>

      <div className="grid sm:grid-cols-[minmax(0,1fr)_240px]">
        <div className="flex flex-col gap-1 px-3.5 py-2.5 sm:px-5 sm:py-3.5">
          <span className="flex items-center gap-2 text-[12px] text-muted sm:text-[13px]">
            <span className="max-sm:hidden">
              <AirlineBadge code={flight.owner.code} />
            </span>
            {flight.owner.name} · <span className="data">{flightNumbersOf(flight)}</span>
          </span>
          {flight.slices.map((s, i) => (
            <SliceTimeline
              key={`${s.origin.code}-${s.destination.code}`}
              slice={s}
              label={flight.slices.length > 1 ? (i === 0 ? "Ida" : "Vuelta") : undefined}
            />
          ))}
        </div>
        <div className="flex flex-col justify-center gap-1.5 border-dashed border-line-dash px-3.5 pb-3 sm:border-l sm:px-5 sm:py-3.5">
          <strong className="text-[14px]">{fareName(fare)}</strong>
          <span className="flex gap-3 text-[13px]">
            {bagMark(bagCell(fareCarryOn(fare), "carry_on"), "Mano")}
            {bagMark(bagCell(fareCheckedBags(fare), "checked"), "Maleta")}
          </span>
          <span className={cn("text-[13px]", toneTextClass(conditions.tone))}>{conditions.text}</span>
          <span className="data text-[16px] font-semibold sm:text-[20px]">
            {formatMoney(fare.price.total)}
          </span>
        </div>
      </div>

      {expired && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 border-t border-warn-line bg-warn-soft px-3.5 py-2.5 text-[14px] text-warn-ink sm:px-5"
        >
          <span className="flex-1">
            El precio de esta tarifa venció. Lo volvemos a consultar con la aerolínea.
          </span>
          <button
            type="button"
            onClick={refresh}
            disabled={refreshing}
            className="h-[38px] rounded-md bg-action px-3.5 font-semibold text-white disabled:opacity-70"
          >
            {refreshing ? "Actualizando…" : "Actualizar precio"}
          </button>
        </div>
      )}

      <div className="grid grid-cols-3 border-t border-line-soft sm:flex sm:flex-wrap sm:gap-2 sm:px-5 sm:pt-2.5 sm:pb-3.5">
        <Link
          to="/flights/$key"
          params={{ key: flight.key }}
          search={{ ...pickSearch(search), fare: fare.offer_id, via: "trip" }}
          className={cn(
            ACTION,
            "justify-center border-action text-action max-sm:h-11 max-sm:rounded-none max-sm:border-0 max-sm:text-[13px]",
          )}
        >
          <span className="sm:hidden">Detalle</span>
          <span className="max-sm:hidden">Ver detalle</span>
        </Link>
        <Link
          to="/flights"
          search={{ ...pickSearch(search), hl: flight.key }}
          className={cn(
            ACTION,
            "justify-center border-line text-ink hover:text-ink max-sm:h-11 max-sm:rounded-none max-sm:border-0 max-sm:border-l max-sm:border-line-soft max-sm:text-[13px] max-sm:text-action",
          )}
        >
          <span className="sm:hidden">Cambiar</span>
          <span className="max-sm:hidden">Cambiar vuelo o tarifa</span>
        </Link>
        <button
          type="button"
          onClick={() => {
            const result = remove(item.itemKey);
            if (result) onRemoved(result);
          }}
          className={cn(
            ACTION,
            "justify-center border-bad-line bg-white text-bad sm:ml-auto max-sm:h-11 max-sm:rounded-none max-sm:border-0 max-sm:border-l max-sm:border-line-soft max-sm:text-[13px]",
          )}
        >
          <TrashIcon className="max-sm:hidden" />
          <span className="sm:hidden">Eliminar</span>
          <span className="max-sm:hidden">Eliminar vuelo</span>
        </button>
      </div>
    </article>
  );
}
