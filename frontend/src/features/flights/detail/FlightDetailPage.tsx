import { Link, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { useMemo } from "react";
import type { Fare, Flight, FlightSegment, FlightSlice } from "@/api/client";
import { useFlightSearch } from "@/api/flights";
import { ClockIcon } from "@/components/icons";
import { StepLinks } from "@/components/layout/Steps";
import { TopBar } from "@/components/layout/TopBar";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import {
  dayOffset,
  formatAmount,
  formatDate,
  formatDuration,
  formatRemaining,
  formatTime,
  isZero,
} from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { useAddToTrip } from "../../trip/useAddToTrip";
import {
  bagCell,
  type Cell,
  conditionCell,
  fareCarryOn,
  fareCheckedBags,
  fareName,
  joinSpanish,
  SHORT_CONNECTION_MINUTES,
  stopsLabel,
  type Tone,
} from "../results/logic";
import { EXPIRY_WARNING_MS } from "../results/ResultStates";
import { flightNumber } from "../results/SliceTimeline";
import { type DetailSearch, isComplete, pickSearch, toCriteria } from "../search/params";

const utcDateTime = (iso: string) =>
  `${formatDate(iso, { year: true })} ${new Date(iso).toISOString().slice(11, 16)} UTC`;
const utcTime = (iso: string) => new Date(iso).toISOString().slice(11, 16);

/** Design board "Detalle de la oferta". */
export function FlightDetailPage() {
  const { key } = useParams({ from: "/flights/$key" });
  const search = useSearch({ from: "/flights/$key" });
  const navigate = useNavigate({ from: "/flights/$key" });
  const complete = isComplete(search) ? search : null;
  const criteriaKey = JSON.stringify(complete ? pickSearch(complete) : null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: recomputed only when the criteria change.
  const criteria = useMemo(() => (complete ? toCriteria(complete) : null), [criteriaKey]);
  // Same query as the results page: comes from the cache, or searches again after a reload.
  const query = useFlightSearch(criteria);
  const addToTrip = useAddToTrip();
  const fromTrip = search.via === "trip";
  const flight = query.data?.flights.find((f) => f.key === key);
  const selected = flight
    ? (flight.fares.find((f) => f.offer_id === search.fare) ?? (flight.fares[0] as Fare))
    : null;

  const backLink = fromTrip ? (
    <Link to="/trip" className="text-[14px]">
      ← Volver a tu viaje
    </Link>
  ) : (
    <Link to="/flights" search={{ ...pickSearch(search), hl: key }} className="text-[14px]">
      ← Volver a resultados
    </Link>
  );

  return (
    <>
      <TopBar className="min-h-14 gap-x-4 gap-y-3">
        <span className="max-sm:hidden">
          <StepLinks current={fromTrip ? 1 : 0} />
        </span>
        <span className="flex-1 sm:hidden" />
        {selected && <ExpiryBadge expiresAt={selected.expires_at} />}
      </TopBar>

      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-5 px-3 pt-3.5 pb-28 sm:px-5 sm:pt-6 sm:pb-16">
        {!complete || query.isPending ? (
          <p className="text-muted">{complete ? "Cargando el vuelo…" : backLink}</p>
        ) : !flight || !selected ? (
          <section className="flex flex-col items-start gap-3">
            {backLink}
            <h1 className="text-[22px] font-bold">Este vuelo ya no está en los resultados</h1>
            <p className="text-ink-2">Las aerolíneas pueden retirar ofertas entre una búsqueda y otra.</p>
          </section>
        ) : (
          <>
            <div className="flex min-w-0 flex-[999_1_640px] flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                {backLink}
                <FlightHeading flight={flight} />
              </div>
              <Itinerary flight={flight} />
              <FareTable
                flight={flight}
                selected={selected}
                onSelect={(fare) =>
                  navigate({ search: (prev) => ({ ...prev, fare: fare.offer_id }), replace: true })
                }
              />
              <FareConditions flight={flight} fare={selected} />
            </div>
            <PriceAside
              flight={flight}
              fare={selected}
              search={search}
              onSave={() => complete && addToTrip(flight, selected, complete, query.data?.search_id ?? "")}
            />
          </>
        )}
      </main>
    </>
  );
}

function ExpiryBadge({ expiresAt }: { expiresAt: string }) {
  const remaining = new Date(expiresAt).getTime() - useNow(1000);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 font-mono text-[13px] font-semibold",
        remaining <= 0
          ? "bg-bad-soft text-bad"
          : remaining < EXPIRY_WARNING_MS
            ? "bg-warn-soft text-warn"
            : "bg-white/10 text-white",
      )}
    >
      <ClockIcon width={14} height={14} />
      {remaining <= 0 ? "Oferta vencida" : `Vence en ${formatRemaining(remaining)}`}
    </span>
  );
}

function FlightHeading({ flight }: { flight: Flight }) {
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

const SECTION = "overflow-hidden rounded-lg border border-line bg-white";
const SECTION_TITLE = "border-b border-line-soft px-[18px] py-3.5 text-[16px] font-semibold";

function Itinerary({ flight }: { flight: Flight }) {
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

function amenityRows(segment: FlightSegment): { k: string; cell: Cell }[] {
  const amenities = segment.cabin?.amenities;
  if (!amenities) return [{ k: "Comodidades", cell: { label: "Sin informar", tone: "na" } }];
  const wifi: Record<string, Cell> = {
    free: { label: "Gratis", tone: "ok" },
    paid: { label: "Pago", tone: "warn" },
    available: { label: "Disponible", tone: "ok" },
    unavailable: { label: "No disponible", tone: "bad" },
  };
  const legroom: Record<string, [string, Tone]> = {
    less: ["menos espacio", "warn"],
    standard: ["estándar", "ok"],
    more: ["más espacio", "ok"],
  };
  const [space, spaceTone] = amenities.legroom
    ? (legroom[amenities.legroom] ?? [amenities.legroom, "na"])
    : [null, "na" as Tone];
  const seat: Cell = amenities.seat_pitch
    ? { label: `${amenities.seat_pitch}″ · ${space ?? "espacio sin dato"}`, tone: space ? spaceTone : "na" }
    : { label: "Sin dato", tone: "na" };
  return [
    {
      k: "Wi-Fi",
      cell: amenities.wifi
        ? (wifi[amenities.wifi] ?? { label: "Sin dato", tone: "na" })
        : { label: "Sin dato", tone: "na" },
    },
    {
      k: "Enchufe",
      cell:
        amenities.power === true
          ? { label: "Sí", tone: "ok" }
          : amenities.power === false
            ? { label: "No", tone: "bad" }
            : { label: "Sin dato", tone: "na" },
    },
    { k: "Asiento", cell: seat },
  ];
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

/** Change or refund in the detail's words: "Con cargo · GBP 300,00". */
function penaltyCell(condition: Fare["conditions"]["change"]): Cell {
  const cell = conditionCell(condition);
  return cell.tone === "warn" ? { ...cell, label: `Con cargo · ${cell.label}` } : cell;
}

const FARE_GRID = "grid grid-cols-[40px_minmax(0,1.4fr)_110px_repeat(4,minmax(0,1fr))] items-center";

function FareTable({
  flight,
  selected,
  onSelect,
}: {
  flight: Flight;
  selected: Fare;
  onSelect: (fare: Fare) => void;
}) {
  return (
    <section aria-labelledby="fares" className={SECTION}>
      <h2 id="fares" className={SECTION_TITLE}>
        Tarifa{" "}
        <span className="text-[13px] font-normal text-muted">
          · {flight.fares.length === 1 ? "1 opción" : `${flight.fares.length} opciones para este mismo vuelo`}
        </span>
      </h2>
      {/* Mobile (design): one radio row per fare with a short summary. */}
      <fieldset className="text-[13px] sm:hidden">
        <legend className="sr-only">Tarifa</legend>
        {flight.fares.map((fare, i) => {
          const checked = bagCell(fareCheckedBags(fare), "checked");
          const carryOn = bagCell(fareCarryOn(fare), "carry_on");
          const change = conditionCell(fare.conditions.change);
          return (
            <label
              key={fare.offer_id}
              className={cn(
                "flex cursor-pointer items-center gap-2.5 px-3 py-2.5",
                i > 0 && "border-t border-line-soft",
                fare.offer_id === selected.offer_id && "bg-action-soft",
              )}
            >
              <input
                type="radio"
                name="fare-mobile"
                checked={fare.offer_id === selected.offer_id}
                onChange={() => onSelect(fare)}
                className="h-[18px] w-[18px] accent-action"
              />
              <span className="flex-1">
                <strong>{fareName(fare)}</strong>
                <span className="block text-muted">
                  Valija {checked.label.toLowerCase()} · mano {carryOn.label.toLowerCase()} · cambio{" "}
                  {change.label.toLowerCase()}
                </span>
              </span>
              <span className="data font-semibold">{formatAmount(fare.price.total)}</span>
            </label>
          );
        })}
      </fieldset>
      <div className="overflow-x-auto max-sm:hidden">
        <fieldset className="min-w-[720px]">
          <legend className="sr-only">Tarifa</legend>
          <div aria-hidden className={cn(FARE_GRID, "field-label border-b border-line-soft bg-surface-2")}>
            <span />
            <span className="px-2 py-2.5">Tarifa</span>
            <span className="px-2 py-2.5 text-right">Total</span>
            <span className="px-2 py-2.5">Valija</span>
            <span className="px-2 py-2.5">Mano</span>
            <span className="px-2 py-2.5">Cambio</span>
            <span className="px-2 py-2.5">Reembolso</span>
          </div>
          {flight.fares.map((fare) => {
            const on = fare.offer_id === selected.offer_id;
            const cells = [
              bagCell(fareCheckedBags(fare), "checked"),
              bagCell(fareCarryOn(fare), "carry_on"),
              penaltyCell(fare.conditions.change),
              penaltyCell(fare.conditions.refund),
            ];
            return (
              <label
                key={fare.offer_id}
                className={cn(
                  FARE_GRID,
                  "w-full cursor-pointer border-b border-line-soft text-left text-[14px] has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-action",
                  on ? "bg-action-soft shadow-[inset_3px_0_0_#1D4ED8]" : "bg-white hover:bg-surface-2",
                )}
              >
                <input
                  type="radio"
                  name="fare"
                  checked={on}
                  onChange={() => onSelect(fare)}
                  className="sr-only"
                />
                <span aria-hidden className="flex justify-center">
                  <span
                    className={cn(
                      "box-border h-4 w-4 rounded-full",
                      on ? "border-[5px] border-action" : "border-2 border-subtle",
                    )}
                  />
                </span>
                <span className="px-2 py-3 font-semibold">{fareName(fare)}</span>
                <span className="data px-2 py-3 text-right font-semibold">
                  {formatAmount(fare.price.total)}
                </span>
                {cells.map((cell, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: fixed columns.
                  <span key={i} className={cn("px-2 py-3", toneTextClass(cell.tone))}>
                    {cell.label}
                  </span>
                ))}
              </label>
            );
          })}
        </fieldset>
      </div>
    </section>
  );
}

function benefitCell(value: boolean | null | undefined, yes: string): Cell {
  if (value === true) return { label: yes, tone: "ok" };
  if (value === false) return { label: "No incluido", tone: "bad" };
  return { label: "Sin dato", tone: "na" };
}

function FareConditions({ flight, fare }: { flight: Flight; fare: Fare }) {
  const benefits = fare.slices[0]?.benefits;
  const penalties = [fare.conditions.change.penalty, fare.conditions.refund.penalty].filter(
    (p): p is NonNullable<typeof p> => Boolean(p) && !isZero(p as NonNullable<typeof p>),
  );
  const penaltyCurrency = penalties[0]?.currency;
  const priceCurrency = fare.price.total.currency;
  const conditions: { k: string; cell: Cell }[] = [
    { k: "Cambio antes de la salida", cell: penaltyCell(fare.conditions.change) },
    { k: "Reembolso antes de la salida", cell: penaltyCell(fare.conditions.refund) },
    { k: "Valija despachada", cell: bagCell(fareCheckedBags(fare), "checked") },
    { k: "Equipaje de mano", cell: bagCell(fareCarryOn(fare), "carry_on") },
    { k: "Selección de asiento anticipada", cell: benefitCell(benefits?.advance_seat_selection, "Incluida") },
    { k: "Embarque prioritario", cell: benefitCell(benefits?.priority_boarding, "Incluido") },
    { k: "Check-in prioritario", cell: benefitCell(benefits?.priority_check_in, "Incluido") },
  ];

  return (
    <section
      aria-labelledby="conditions"
      className="flex flex-col gap-3 rounded-lg border border-line bg-white px-[18px] py-4"
    >
      <h2 id="conditions" className="text-[16px] font-semibold">
        Condiciones de {fareName(fare)}
      </h2>
      <div className="grid gap-2.5 text-[14px] sm:[grid-template-columns:repeat(auto-fit,minmax(220px,1fr))]">
        {conditions.map(({ k, cell }) => (
          <div key={k} className="flex flex-col gap-1 rounded-md border border-line-soft px-3 py-2.5">
            <span className="text-[12px] text-muted">{k}</span>
            <span className={toneTextClass(cell.tone)}>{cell.label}</span>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-muted">
        {penaltyCurrency && penaltyCurrency !== priceCurrency
          ? `Las penalidades las informa la aerolínea en ${penaltyCurrency}; el precio está en ${priceCurrency}. Se muestran en su moneda original, sin convertir. `
          : "«Sin dato»: la aerolínea no lo informa para esta tarifa. "}
        {flight.owner.conditions_of_carriage_url && (
          <>
            Ver{" "}
            <a href={flight.owner.conditions_of_carriage_url} target="_blank" rel="noreferrer">
              condiciones de transporte de {flight.owner.name}
            </a>
            .
          </>
        )}
      </p>
    </section>
  );
}

function PriceAside({
  flight,
  fare,
  search,
  onSave,
}: {
  flight: Flight;
  fare: Fare;
  search: DetailSearch;
  onSave: () => void;
}) {
  const expired = new Date(fare.expires_at).getTime() <= useNow(1000);
  const { base, taxes, total } = fare.price;
  const passengers = (search.adults ?? 1) + (search.children?.length ?? 0);
  const basePct = base && taxes ? Math.round((Number(base.amount) / Number(total.amount)) * 100) : null;
  const saveButton = (className: string, short = false) =>
    expired ? (
      <Link
        to="/flights"
        search={{ ...pickSearch(search), hl: flight.key }}
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-action px-4 font-semibold text-white hover:text-white",
          className,
        )}
      >
        {short ? "Actualizar precios" : "La oferta venció · actualizar precios"}
      </Link>
    ) : (
      <button
        type="button"
        onClick={onSave}
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-action px-4 font-semibold text-white hover:bg-action-hover",
          className,
        )}
      >
        {short ? "Guardar en mi viaje" : `Guardar ${fareName(fare)} en mi viaje`}
      </button>
    );

  return (
    <>
      <aside
        aria-label="Resumen del precio"
        className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-3 max-sm:max-w-none"
      >
        <div className="flex flex-col gap-3 rounded-lg border border-line bg-white p-[18px]">
          <span className="text-[12px] font-semibold tracking-[0.06em] text-muted uppercase">
            Precio · {passengers === 1 ? "1 adulto" : `${passengers} pasajeros`}
          </span>
          <div className="flex justify-between text-[14px]">
            <span>Tarifa base</span>
            <span className="data">{base ? formatAmount(base) : "Sin dato"}</span>
          </div>
          <div className="flex justify-between text-[14px]">
            <span>Impuestos y cargos</span>
            <span className="data">{taxes ? formatAmount(taxes) : "Sin dato"}</span>
          </div>
          {basePct !== null && (
            <>
              <div aria-hidden className="flex h-2 overflow-hidden rounded bg-line">
                <span className="bg-action" style={{ width: `${basePct}%` }} />
              </div>
              <p className="text-[12px] text-muted">
                La tarifa base es el {basePct} % del total; el resto son impuestos y cargos de aeropuerto.
              </p>
            </>
          )}
          <div className="flex items-baseline justify-between border-t border-line-soft pt-3">
            <span className="font-semibold">Total</span>
            <span className="data text-[24px] font-semibold">
              {formatAmount(total)} <span className="text-[13px]">{total.currency}</span>
            </span>
          </div>
          <div className="flex justify-between text-[13px] text-ink-2">
            <span>CO₂ estimado</span>
            <span className="data">
              {flight.emissions_kg !== null ? `${flight.emissions_kg} kg` : "Sin dato"}
            </span>
          </div>
          {saveButton("max-sm:hidden")}
        </div>
        {fare.payment.can_hold && fare.payment.payment_required_by && (
          <div className="flex flex-col gap-1.5 rounded-lg border border-line bg-white px-4 py-3.5 text-[13px] leading-normal">
            <strong className="text-[14px]">Reservá ahora, pagá después</strong>
            <span>
              Esta tarifa se puede reservar sin pagar y pagar hasta el{" "}
              <strong className="font-mono">{utcDateTime(fare.payment.payment_required_by)}</strong>. La
              elección se hace en el paso de pago.
            </span>
          </div>
        )}
        <div className="rounded-lg border border-warn-line bg-warn-soft px-4 py-3.5 text-[13px] leading-normal text-warn-ink">
          <strong className="block text-[14px]">
            {expired ? "La oferta venció" : `La oferta vence a las ${utcTime(fare.expires_at)} UTC`}
          </strong>
          Antes de reservar se vuelve a confirmar el precio con la aerolínea. Si cambió, se avisa antes de
          cobrar.
        </div>
      </aside>

      <div className="fixed inset-x-0 bottom-0 z-20 flex items-center gap-3 border-t border-line bg-white px-3.5 pt-3 pb-5 sm:hidden">
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="data text-[18px] font-semibold whitespace-nowrap">
            {formatAmount(total)} {total.currency}
          </span>
          <MobileExpiry expiresAt={fare.expires_at} />
        </span>
        {saveButton("text-[15px]", true)}
      </div>
    </>
  );
}

function MobileExpiry({ expiresAt }: { expiresAt: string }) {
  const remaining = new Date(expiresAt).getTime() - useNow(1000);
  return (
    <span
      className={cn("text-[11px] font-semibold", remaining < EXPIRY_WARNING_MS ? "text-warn" : "text-muted")}
    >
      {remaining <= 0 ? "Oferta vencida" : `Vence en ${formatRemaining(remaining)}`}
    </span>
  );
}
