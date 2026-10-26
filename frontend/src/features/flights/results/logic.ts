/**
 * Pure rules of the results page: filters, sort, tags and how each fare value is shown.
 * Kept apart from the components so they can be tested with the real API response.
 */
import type { Fare, FareCondition, Flight, FlightSlice } from "@/api/client";
import { formatDuration, formatPenalty, isZero } from "@/lib/format";
import type { ResultsSearch, SORTS, TIME_WINDOWS } from "../search/params";

export type SortKey = (typeof SORTS)[number];
export type TimeWindow = (typeof TIME_WINDOWS)[number];

export interface ResultFilters {
  direct?: boolean;
  bag?: boolean;
  refund?: boolean;
  time?: TimeWindow;
  airlines?: string[];
}

/** Connections shorter than this are highlighted (design: "Conexión corta"). */
export const SHORT_CONNECTION_MINUTES = 60;

/** Duffel's test airline. */
export const TEST_AIRLINE = "ZZ";

export const TIME_WINDOW_LABELS: Record<TimeWindow, string> = {
  morning: "Mañana (antes de 12:00)",
  afternoon: "Tarde (12:00 a 18:00)",
  evening: "Noche (después de 18:00)",
};

export function filtersFromSearch(search: ResultsSearch): ResultFilters {
  return {
    direct: search.fDirect,
    bag: search.fBag,
    refund: search.fRefund,
    time: search.fTime,
    airlines: search.fAirlines?.length ? search.fAirlines : undefined,
  };
}

export function activeFilterCount(filters: ResultFilters): number {
  return (Object.keys(filters) as (keyof ResultFilters)[]).filter((k) => isActive(filters, k)).length;
}

function isActive(filters: ResultFilters, key: keyof ResultFilters): boolean {
  const value = filters[key];
  return Array.isArray(value) ? value.length > 0 : Boolean(value);
}

// --- Fare values ---

/** Checked bags of the fare on the whole trip: the lowest of every slice and passenger; `null` if any is unknown. */
export function fareCheckedBags(fare: Fare): number | null {
  return lowest(fare.slices.flatMap((s) => s.baggage.map((b) => b.checked ?? null)));
}

/** Cabin bags of the fare on the whole trip; `null` if any is unknown. */
export function fareCarryOn(fare: Fare): number | null {
  return lowest(fare.slices.flatMap((s) => s.baggage.map((b) => b.carry_on ?? null)));
}

function lowest(values: (number | null)[]): number | null {
  if (values.length === 0 || values.some((v) => v === null)) return null;
  return Math.min(...(values as number[]));
}

/** "Con valija" only counts a checked bag the airline reports; unknown doesn't count. */
export function fareHasCheckedBag(fare: Fare): boolean {
  return (fareCheckedBags(fare) ?? 0) >= 1;
}

export function fareIsRefundable(fare: Fare): boolean {
  return fare.conditions.refund.allowed === true;
}

/** Fare names of every slice, e.g. "Economy Light" or "Basic / Economy Flex". */
export function fareName(fare: Fare): string {
  const names = [...new Set(fare.slices.map((s) => s.fare_brand).filter(Boolean))];
  return names.length ? names.join(" / ") : "Tarifa";
}

export type Tone = "ok" | "warn" | "bad" | "na";

export interface Cell {
  label: string;
  tone: Tone;
}

/** `null` → «Sin dato»; 0 → «No incluida»; n → «n incluida(s)». */
export function bagCell(quantity: number | null, kind: "checked" | "carry_on"): Cell {
  if (quantity === null) return { label: "Sin dato", tone: "na" };
  const [one, many, none] =
    kind === "checked" ? ["incluida", "incluidas", "No incluida"] : ["incluido", "incluidos", "No incluido"];
  if (quantity === 0) return { label: none, tone: "bad" };
  return { label: `${quantity} ${quantity === 1 ? one : many}`, tone: "ok" };
}

/** Change or refund: «No permite», «Gratis», the penalty in its own currency, or «Sin dato». */
export function conditionCell(condition: FareCondition): Cell {
  if (condition.allowed === false) return { label: "No permite", tone: "bad" };
  if (condition.allowed !== true) return { label: "Sin dato", tone: "na" };
  if (!condition.penalty) return { label: "Permite · cargo sin dato", tone: "na" };
  if (isZero(condition.penalty)) return { label: "Gratis", tone: "ok" };
  return { label: formatPenalty(condition.penalty), tone: "warn" };
}

// --- Flights ---

export function isDirect(flight: Flight): boolean {
  return flight.slices.every((s) => s.stops === 0);
}

export function departureOf(flight: Flight): string {
  return flight.slices[0]?.segments[0]?.departing_at ?? "";
}

export function totalDuration(flight: Flight): number {
  return flight.slices.reduce((sum, s) => sum + (s.duration_minutes ?? 0), 0);
}

export function timeWindowOf(localDateTime: string): TimeWindow {
  const hour = Number(localDateTime.slice(11, 13));
  if (hour < 12) return "morning";
  return hour < 18 ? "afternoon" : "evening";
}

/** Keeps the flights and fares that match every filter; flights without matching fares are dropped. */
export function applyFilters(flights: Flight[], filters: ResultFilters): Flight[] {
  const result: Flight[] = [];
  for (const flight of flights) {
    if (filters.direct && !isDirect(flight)) continue;
    if (filters.time && timeWindowOf(departureOf(flight)) !== filters.time) continue;
    if (filters.airlines?.length && !filters.airlines.includes(flight.owner.code)) continue;
    const fares = flight.fares.filter(
      (fare) => (!filters.bag || fareHasCheckedBag(fare)) && (!filters.refund || fareIsRefundable(fare)),
    );
    if (fares.length === 0) continue;
    // Same object when no fare was dropped, so memoized cards of unchanged flights don't re-render.
    result.push(
      fares.length === flight.fares.length
        ? flight
        : { ...flight, fares, lowest_price: (fares[0] as Fare).price.total },
    );
  }
  return result;
}

export function sortFlights(flights: Flight[], sort: SortKey = "price"): Flight[] {
  const byPrice = (a: Flight, b: Flight) => Number(a.lowest_price.amount) - Number(b.lowest_price.amount);
  const compare: Record<SortKey, (a: Flight, b: Flight) => number> = {
    price: byPrice,
    duration: (a, b) => totalDuration(a) - totalDuration(b) || byPrice(a, b),
    departure: (a, b) => departureOf(a).localeCompare(departureOf(b)) || byPrice(a, b),
  };
  return [...flights].sort(compare[sort]);
}

export interface RelaxSuggestion {
  filter: keyof ResultFilters;
  count: number;
}

/** When filters leave nothing: how many flights there would be without each active filter. */
export function relaxSuggestions(flights: Flight[], filters: ResultFilters): RelaxSuggestion[] {
  return (Object.keys(filters) as (keyof ResultFilters)[])
    .filter((key) => isActive(filters, key))
    .map((key) => ({ filter: key, count: applyFilters(flights, { ...filters, [key]: undefined }).length }))
    .filter((s) => s.count > 0)
    .sort((a, b) => b.count - a.count);
}

export function airlinesOf(flights: Flight[]): { code: string; name: string }[] {
  const byCode = new Map(flights.map((f) => [f.owner.code, f.owner.name]));
  return [...byCode].map(([code, name]) => ({ code, name })).sort((a, b) => a.name.localeCompare(b.name));
}

// --- Card details ---

/** "Operado por SWISS" / "Operado por City Airlines, Lufthansa y SWISS". */
export function operatorsLabel(slice: FlightSlice): string {
  const names = [...new Set(slice.segments.map((s) => s.operating_carrier.name))];
  return `Operado por ${joinSpanish(names)}`;
}

export function joinSpanish(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} y ${items.at(-1)}`;
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
export function stopMarkers(slice: FlightSlice): StopMarker[] {
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

export interface FlightTag {
  label: string;
  tone: "ok" | "warn" | "info" | "neutral";
}

/** Flights that physically are the same aircraft (same operating flights at the same times). */
function operatingSignature(flight: Flight): string {
  return flight.slices
    .map((s) => s.segments.map((g) => `${g.operating_carrier.code}@${g.departing_at}`).join(">"))
    .join("|");
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

/** What a card shows about its flight relative to the others in the list. */
export interface FlightInsight {
  tag: FlightTag | null;
  note: string;
}

/**
 * Tag and note of every flight of a list, in one pass.
 *
 * Both depend on the other flights (cheapest, same aircraft), so they're computed once per list:
 * doing it per card is O(n²) and froze the page with ~2,000 flights.
 */
export function flightInsights(flights: Flight[]): Map<string, FlightInsight> {
  const cheapest = Math.min(...flights.map((f) => Number(f.lowest_price.amount)));
  const signatures = new Map(flights.map((f) => [f.key, operatingSignature(f)]));
  const bySignature = new Map<string, Flight[]>();
  for (const flight of flights) {
    const signature = signatures.get(flight.key) as string;
    bySignature.set(signature, [...(bySignature.get(signature) ?? []), flight]);
  }

  return new Map(
    flights.map((flight) => {
      const twin = bySignature
        .get(signatures.get(flight.key) as string)
        ?.find((other) => other.key !== flight.key);
      const short = flight.slices.flatMap(stopMarkers).filter((m) => m.short);
      return [flight.key, { tag: tagFor(flight, cheapest, short, twin), note: noteFor(flight, short, twin) }];
    }),
  );
}

/** One tag per card, by priority: cheapest, short connection, same aircraft as another option, test airline. */
function tagFor(
  flight: Flight,
  cheapest: number,
  short: StopMarker[],
  twin: Flight | undefined,
): FlightTag | null {
  if (Number(flight.lowest_price.amount) === cheapest) return { label: "Más barato", tone: "ok" };
  if (short.length === 1) {
    const [only] = short as [StopMarker];
    return { label: `Conexión corta en ${only.airport} · ${formatDuration(only.minutes)}`, tone: "warn" };
  }
  if (short.length > 1) {
    return {
      label: `Conexiones cortas · ${joinSpanish(short.map((m) => formatDuration(m.minutes)))}`,
      tone: "warn",
    };
  }
  if (twin) return { label: "Mismo avión que otra opción", tone: "info" };
  if (flight.owner.code === TEST_AIRLINE) return { label: "Aerolínea de prueba", tone: "neutral" };
  return null;
}

/** Note under the fare matrix (design): what to watch for in this flight. */
function noteFor(flight: Flight, short: StopMarker[], twin: Flight | undefined): string {
  if (twin) return `Mismo avión que ${flightNumbersOf(twin)}: compará qué incluye cada una.`;
  if (short.length > 0) {
    return `${short.length === 1 ? "Conexión corta" : "Conexiones cortas"}: ${joinSpanish(
      short.map((m) => `${formatDuration(m.minutes)} en ${m.airport}`),
    )}.`;
  }
  return flight.fares.length > 1
    ? "Penalidades en la moneda que informa la aerolínea."
    : "Una sola tarifa para este vuelo.";
}

/** Tag of one flight within `all` (convenience for a single card; lists use `flightInsights`). */
export function flightTag(flight: Flight, all: Flight[]): FlightTag | null {
  return flightInsights(all).get(flight.key)?.tag ?? null;
}

// --- Round trips in two steps ---

/**
 * Whether the results are a round trip, always shown in two steps: each outbound once, then the
 * returns of the chosen one. Decided on the whole response, not on the filtered list.
 */
export function isRoundTrip(flights: Flight[]): boolean {
  return flights.length > 0 && flights.every((f) => f.slices.length === 2);
}

/** Short, stable hash for URL keys. */
function hash(text: string): string {
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

/** Identifies an outbound: same seller and same flights at the same times. */
export function outboundKeyOf(flight: Flight): string {
  const outbound = flight.slices[0];
  const segments = outbound?.segments.map(
    (s) => `${s.marketing_carrier.code}${s.flight_number}@${s.departing_at}`,
  );
  return hash(`${flight.owner.code}|${segments?.join(">")}`);
}

export interface OutboundOption {
  key: string;
  /** For the card: the outbound slice only, priced at the cheapest combination. */
  flight: Flight;
  /** Every combination (outbound + return) with this outbound, in list order. */
  returns: Flight[];
}

/**
 * Each outbound once, with its combinations. The search stays a round trip (combined fares are
 * usually cheaper than two one-ways); only how the results are shown changes.
 *
 * Keeps the order of `flights` (already filtered and sorted): an outbound appears where its best
 * combination is.
 */
export function groupByOutbound(flights: Flight[]): OutboundOption[] {
  const groups = new Map<string, Flight[]>();
  for (const flight of flights) {
    const key = outboundKeyOf(flight);
    const group = groups.get(key);
    if (group) group.push(flight);
    else groups.set(key, [flight]);
  }
  return [...groups].map(([key, returns]) => {
    const cheapest = returns.reduce((a, b) =>
      Number(b.lowest_price.amount) < Number(a.lowest_price.amount) ? b : a,
    );
    const outbound = cheapest.slices[0] as FlightSlice;
    return {
      key,
      returns,
      flight: { ...cheapest, key, slices: [outbound], lowest_price: cheapest.lowest_price },
    };
  });
}

/** For the card of a return: the combination showing only its return slice. */
export function returnView(flight: Flight): Flight {
  return { ...flight, slices: flight.slices.slice(1) };
}
