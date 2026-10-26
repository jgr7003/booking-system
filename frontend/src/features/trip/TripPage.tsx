import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import type { Money } from "@/api/client";
import { flightKeys, searchFlights } from "@/api/flights";
import { ClockIcon, HotelIcon, LogoIcon, TrashIcon } from "@/components/icons";
import { StepCircles, StepCount } from "@/components/layout/Steps";
import { TopBar } from "@/components/layout/TopBar";
import { useToasts } from "@/components/ui/toast";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import {
  formatAmount,
  formatDate,
  formatMoney,
  formatPassengers,
  formatRemaining,
  formatShortDate,
} from "@/lib/format";
import { searchedCity } from "@/lib/placeLabels";
import { useNow } from "@/lib/useNow";
import { AirlineBadge } from "../flights/results/FlightCard";
import {
  bagCell,
  type Cell,
  conditionCell,
  fareCarryOn,
  fareCheckedBags,
  fareName,
  flightNumbersOf,
} from "../flights/results/logic";
import { EXPIRY_WARNING_MS } from "../flights/results/ResultStates";
import { SliceTimeline } from "../flights/results/SliceTimeline";
import { pickSearch, toCriteria } from "../flights/search/params";
import { makeTripItem, type TripItem, tripItems, useTrip } from "./store";

/** Design board "Tu viaje". */
export function TripPage() {
  // Raw state with a shallow comparison; deriving the list inside the selector would loop renders.
  const state = useTrip(useShallow((s) => ({ items: s.items, order: s.order })));
  const items = useMemo(() => tripItems(state), [state]);
  const restore = useTrip((s) => s.restore);
  const [removed, setRemoved] = useState<{ item: TripItem; index: number } | null>(null);
  const last = items.at(-1);
  // The searched destination, not the airport the flight lands at (NYC, not EWR).
  const destination = last ? searchedCity(last.search.to, last.flight.slices[0]?.destination) : null;
  const title = destination ? `Tu viaje a ${destination}` : "Tu viaje está vacío";

  return (
    <>
      <TopBar>
        <span className="flex-1" />
        <span className="max-sm:hidden">
          <StepCircles current={1} canOpenTrip />
        </span>
        <span className="sm:hidden">
          <StepCount current={1} />
        </span>
      </TopBar>

      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-5 px-3 pt-3.5 pb-28 sm:px-5 sm:pt-6 sm:pb-14">
        <section aria-labelledby="trip-title" className="flex min-w-0 flex-[999_1_640px] flex-col gap-3.5">
          <div className="flex flex-col gap-1">
            <h1 id="trip-title" className="text-[22px] font-bold sm:text-[28px]">
              {title}
            </h1>
            <p className="text-[15px] text-ink-2">
              {items.length
                ? "Revisá tu vuelo y seguí con los datos del pasajero."
                : "Buscá un vuelo para empezar."}
            </p>
          </div>

          {items.map((item, i) => (
            <TripItemCard
              key={item.itemKey}
              item={item}
              position={i + 1}
              onRemoved={(result) => setRemoved(result)}
            />
          ))}

          {removed && (
            <div
              role="status"
              className="flex items-center justify-between gap-3 rounded-lg bg-ink px-4 py-2.5 text-[14px] text-white"
            >
              <span>
                Quitaste el vuelo {removed.item.flight.slices[0]?.origin.code} →{" "}
                {removed.item.flight.slices[0]?.destination.code} del{" "}
                {formatShortDate(removed.item.search.depart)}.
              </span>
              <button
                type="button"
                onClick={() => {
                  restore(removed.item, removed.index);
                  setRemoved(null);
                }}
                className="h-[38px] rounded-md border border-muted-2 px-3.5 font-semibold"
              >
                Deshacer
              </button>
            </div>
          )}

          <div className="grid gap-2.5 sm:grid-cols-2">
            {/* For now a trip is a single flight for one traveler: more flights and hotels come later. */}
            {items.length ? (
              <button type="button" disabled title="Próximamente" className={COMING_SOON}>
                <LogoIcon width={18} height={18} />
                Agregar otro vuelo · próximamente
              </button>
            ) : (
              <Link
                to="/"
                className="inline-flex h-[52px] items-center justify-center gap-2 rounded-lg border border-dashed border-action bg-white text-[15px] font-semibold text-action sm:h-14"
              >
                <LogoIcon width={18} height={18} />
                Buscar vuelo
              </Link>
            )}
            <button type="button" disabled title="Próximamente" className={COMING_SOON}>
              <HotelIcon />
              Agregar hotel · próximamente
            </button>
          </div>
        </section>

        <TripSummary items={items} />
      </main>
    </>
  );
}

const COMING_SOON =
  "inline-flex h-[52px] items-center justify-center gap-2 rounded-lg border border-dashed border-line-dash bg-white text-[15px] font-semibold text-subtle sm:h-14";

const ACTION = "inline-flex h-[38px] items-center gap-1.5 rounded-md border px-3.5 text-[14px] font-semibold";

/** Short summary of what a fare includes, colored like the design ("✓ Mano ✓ Valija"). */
function bagMark(cell: Cell, label: string) {
  const mark = cell.tone === "ok" ? "✓" : cell.tone === "bad" ? "✗" : "?";
  return (
    <span className={toneTextClass(cell.tone)} title={`${label}: ${cell.label}`}>
      {mark} {label}
    </span>
  );
}

function conditionsLine(item: TripItem): { text: string; tone: Cell["tone"] } {
  const change = conditionCell(item.fare.conditions.change);
  const refund = conditionCell(item.fare.conditions.refund);
  const changeText =
    change.tone === "ok"
      ? "Cambio gratis"
      : change.tone === "warn"
        ? `Cambio ${change.label}`
        : `Cambio: ${change.label.toLowerCase()}`;
  const refundText =
    refund.tone === "bad"
      ? "sin reembolso"
      : refund.tone === "ok"
        ? "reembolso gratis"
        : refund.tone === "warn"
          ? `reembolso ${refund.label}`
          : `reembolso: ${refund.label.toLowerCase()}`;
  const tone = change.tone === "ok" && refund.tone === "ok" ? "ok" : change.tone === "bad" ? "bad" : "warn";
  return { text: `${changeText} · ${refundText}`, tone };
}

function TripItemCard({
  item,
  position,
  onRemoved,
}: {
  item: TripItem;
  position: number;
  onRemoved: (removed: { item: TripItem; index: number }) => void;
}) {
  const remove = useTrip((s) => s.remove);
  const add = useTrip((s) => s.add);
  const show = useToasts((s) => s.show);
  const queryClient = useQueryClient();
  const now = useNow(1000);
  const [refreshing, setRefreshing] = useState(false);
  const remaining = new Date(item.fare.expires_at).getTime() - now;
  const expired = remaining <= 0;
  const { flight, fare, search } = item;
  const conditions = conditionsLine(item);

  async function refreshPrice() {
    setRefreshing(true);
    try {
      // A new search: the previous offers expired, so the cached results can't be reused.
      const criteria = toCriteria(search);
      const fresh = await queryClient.fetchQuery({
        queryKey: flightKeys.search(criteria),
        queryFn: ({ signal }) => searchFlights(criteria, signal),
        staleTime: 0,
      });
      const sameFlight = fresh.flights.find((f) => f.key === flight.key);
      const sameFare = sameFlight?.fares.find((f) => fareName(f) === fareName(fare));
      if (sameFlight && sameFare) {
        add(makeTripItem(sameFlight, sameFare, search, fresh.search_id));
        show({ message: `Precio actualizado: ${formatMoney(sameFare.price.total)}.` });
      } else {
        show({ message: "Ese vuelo o tarifa ya no está disponible. Elegí otra opción en los resultados." });
      }
    } catch {
      show({ message: "No pudimos actualizar el precio. Probá de nuevo en unos segundos." });
    } finally {
      setRefreshing(false);
    }
  }

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
            expired
              ? "bg-bad-soft text-bad"
              : remaining < EXPIRY_WARNING_MS
                ? "bg-warn-soft text-warn"
                : "bg-canvas text-ink-2",
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
            {bagMark(bagCell(fareCheckedBags(fare), "checked"), "Valija")}
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
            onClick={refreshPrice}
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

/** Adds amounts per currency: offers in different currencies are never converted. */
function totalsByCurrency(amounts: Money[]): Money[] {
  const totals = new Map<string, number>();
  for (const money of amounts) {
    totals.set(money.currency, (totals.get(money.currency) ?? 0) + Math.round(Number(money.amount) * 100));
  }
  return [...totals].map(([currency, cents]) => ({ currency, amount: (cents / 100).toFixed(2) }));
}

/** "Resumen del viaje" (design). On mobile, the total and the button stick to the bottom. */
function TripSummary({ items }: { items: TripItem[] }) {
  const first = items[0];
  const passengers = first
    ? formatPassengers(first.search.adults ?? 1, first.search.children?.length ?? 0)
    : "1 adulto";
  const totals = totalsByCurrency(items.map((i) => i.fare.price.total));
  const continueButton = (label: string, className: string) => (
    <button
      type="button"
      disabled
      title="La carga de pasajeros llega en la próxima etapa"
      className={cn(
        "flex h-12 shrink-0 items-center justify-center rounded-md bg-line-soft font-semibold text-muted",
        className,
      )}
    >
      {label}
    </button>
  );

  return (
    <>
      <aside
        aria-labelledby="summary-title"
        className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-2.5 rounded-lg border border-line bg-white p-[18px] max-sm:max-w-none"
      >
        <h2 id="summary-title" className="text-[12px] font-semibold tracking-[0.06em] text-muted uppercase">
          Resumen del viaje
        </h2>
        {items.length === 0 && (
          <div className="flex justify-between text-[14px]">
            <span>Vuelos</span>
            <span>—</span>
          </div>
        )}
        {items.map((item) => {
          const slice = item.flight.slices[0];
          return (
            <div key={item.itemKey} className="flex justify-between gap-2 text-[14px]">
              <span>
                Vuelo {slice?.origin.code} → {slice?.destination.code}
              </span>
              <span className="data font-semibold">{formatAmount(item.fare.price.total)}</span>
            </div>
          );
        })}
        <div className="flex justify-between text-[14px] text-muted">
          <span>Hotel</span>
          <span>Sin agregar</span>
        </div>
        <div className="flex items-baseline justify-between border-t border-line-soft pt-2.5">
          <strong>Total · {passengers}</strong>
          <span className="data text-right text-[22px] font-semibold">
            {totals.length === 0
              ? "—"
              : totals.map((t) => (
                  <span key={t.currency} className="block">
                    {formatMoney(t)}
                  </span>
                ))}
          </span>
        </div>
        {continueButton("Continuar a pasajeros · próximamente", "max-sm:hidden")}
        <p className="text-[12px] leading-normal text-muted">
          Cada vuelo es una oferta distinta de su aerolínea: tiene su propio vencimiento y se reserva como una
          orden separada. Si alguno cambia de precio al reconfirmar, se avisa antes de cobrar.
        </p>
      </aside>

      {items.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 flex items-center gap-3 border-t border-line bg-white px-3.5 pt-3 pb-5 sm:hidden">
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="text-[11px] text-muted">Total del viaje</span>
            <strong className="data text-[18px] whitespace-nowrap">
              {totals.map((t) => formatMoney(t)).join(" + ")}
            </strong>
          </span>
          {continueButton("Continuar", "px-[18px]")}
        </div>
      )}
    </>
  );
}
