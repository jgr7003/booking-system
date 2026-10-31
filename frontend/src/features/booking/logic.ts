import type { Booking, FailureCode, FareCondition, OrderSlice } from "@/api/client";
import type { Tone } from "@/lib/cell";
import { lowest } from "@/lib/flights/fares";
import { formatDate, formatPenalty, isZero } from "@/lib/format";

/**
 * Rules of the confirmation screen (design board "Confirmación", Propuesta A v2, and its
 * developer notes). The confirmation email applies the same rules in the backend.
 */

export type Order = NonNullable<Booking["order"]>;

export interface Item {
  label: string;
  value: string;
  tone: Tone;
}

/** Titles as the design writes them before the name. */
export const TITLES: Record<string, string> = {
  mr: "Sr.",
  mrs: "Sra.",
  ms: "Sra./Srta.",
  miss: "Srta.",
  dr: "Dr./Dra.",
};

/** "Sr. PEPE PEREZ": the name goes as the airline got it, in capitals. */
export function passengerName(booking: Booking, withTitle = true): string {
  const name = `${booking.passenger.given_name} ${booking.passenger.family_name}`;
  return withTitle ? `${TITLES[booking.passenger.title] ?? ""} ${name}`.trim() : name;
}

export function isRoundTrip(order: Order): boolean {
  return order.slices.length > 1;
}

/** City of a place, or its IATA code when the provider doesn't say (state 3). */
export function cityOf(place: { code: string; city?: string | null }): string {
  return place.city || place.code;
}

/** Local date of a slice: the date part of its first departure, read as text. */
export function sliceDate(slice: OrderSlice): string {
  return slice.segments[0]?.departing_at.slice(0, 10) ?? "";
}

/** Calendar days an arrival is after its departure: 1 shows "+1". */
export function daysLater(departingAt: string, arrivingAt: string): number {
  const day = (v: string) =>
    Date.UTC(Number(v.slice(0, 4)), Number(v.slice(5, 7)) - 1, Number(v.slice(8, 10)));
  return Math.round((day(arrivingAt) - day(departingAt)) / 86_400_000);
}

/** "Terminal 2" or «terminal s/d». */
export function terminalLabel(terminal: string | null | undefined, short = false): string {
  if (!terminal) return "terminal s/d";
  return short ? `T${terminal}` : `Terminal ${terminal}`;
}

export function sliceBags(slice: OrderSlice): { carryOn: number | null; checked: number | null } {
  const passengers = slice.segments.flatMap((s) => s.passengers);
  return {
    carryOn: lowest(passengers.map((p) => p.baggage.carry_on)),
    checked: lowest(passengers.map((p) => p.baggage.checked)),
  };
}

/** "✓ 1 de mano · ✓ 1 maleta" (line under each flight); `null` when nothing is known. */
export function bagsLine(bags: { carryOn: number | null; checked: number | null }): {
  text: string;
  tone: Tone;
} {
  if (bags.carryOn === null && bags.checked === null) return { text: "Equipaje: Sin dato", tone: "na" };
  const carry =
    bags.carryOn === null
      ? "Mano: sin dato"
      : bags.carryOn === 0
        ? "✗ Mano no incluida"
        : `✓ ${bags.carryOn} de mano`;
  const checked =
    bags.checked === null
      ? "Maleta: sin dato"
      : bags.checked === 0
        ? "✗ Maleta no incluida"
        : `✓ ${bags.checked} ${bags.checked === 1 ? "maleta" : "maletas"}`;
  const tone = bags.carryOn === 0 || bags.checked === 0 ? "warn" : bags.carryOn && bags.checked ? "ok" : "na";
  return { text: `${carry} · ${checked}`, tone };
}

function bagItem(label: string, quantity: number | null, one: string, many: string, none: string): Item {
  if (quantity === null) return { label, value: "Sin dato", tone: "na" };
  if (quantity === 0) return { label, value: `✗ ${none}`, tone: "bad" };
  return { label, value: `✓ ${quantity} ${quantity === 1 ? one : many}`, tone: "ok" };
}

/** Change or refund: «✗ No permite», «✓ Gratis», «Con cargo · 40 USD» or «Sin dato». */
export function conditionItem(label: string, condition: FareCondition): Item {
  if (condition.allowed === false) return { label, value: "✗ No permite", tone: "bad" };
  if (condition.allowed !== true || !condition.penalty) return { label, value: "Sin dato", tone: "na" };
  if (isZero(condition.penalty)) return { label, value: "✓ Gratis", tone: "ok" };
  return { label, value: `Con cargo · ${formatPenalty(condition.penalty)}`, tone: "warn" };
}

function benefitItem(
  label: string,
  value: boolean | null | undefined,
  included: string,
  notIncluded: string,
): Item {
  if (value === null || value === undefined) return { label, value: "Sin dato", tone: "na" };
  return value
    ? { label, value: `✓ ${included}`, tone: "ok" }
    : { label, value: `✗ ${notIncluded}`, tone: "bad" };
}

/** "Qué incluye tu tarifa" of one slice: its bags and benefits, and the order's conditions. */
export function includedItems(slice: OrderSlice, order: Order): Item[] {
  const bags = sliceBags(slice);
  return [
    bagItem("Equipaje de mano", bags.carryOn, "incluido", "incluidos", "No incluido"),
    bagItem("Maleta de bodega", bags.checked, "incluida", "incluidas", "No incluida"),
    conditionItem("Cambios", order.conditions.change),
    conditionItem("Reembolso", order.conditions.refund),
    benefitItem("Selección de asiento", slice.benefits.advance_seat_selection, "Incluida", "No incluida"),
    benefitItem("Embarque prioritario", slice.benefits.priority_boarding, "Incluido", "No incluido"),
  ];
}

/** Whether every slice includes the same: then it's shown once ("Igual en la ida y en la vuelta"). */
export function sameIncluded(order: Order): boolean {
  const [first, ...rest] = order.slices.map((s) => JSON.stringify(includedItems(s, order)));
  return rest.every((r) => r === first);
}

/** Fare names of the order: "Basic" or "Basic / Flex". */
export function fareNames(order: Order): string {
  return [...new Set(order.slices.map((s) => s.fare_brand ?? "Tarifa"))].join(" / ");
}

export interface ManageRow {
  key: "change" | "cancel" | "update";
  title: string;
  detail: string;
  icon: string;
}

/** One row per `available_actions` value, crossed with the conditions (they can't be used yet). */
export function manageRows(order: Order): ManageRow[] {
  const fare = fareNames(order);
  const { change, refund } = order.conditions;
  const changeDetail =
    change.allowed === false
      ? `Tu tarifa ${fare} no permite cambios.`
      : change.allowed && change.penalty
        ? isZero(change.penalty)
          ? "Tu tarifa permite cambios sin cargo."
          : `Con cargo de ${formatPenalty(change.penalty)}.`
        : "Consulta las condiciones con la aerolínea.";
  const cancelDetail =
    refund.allowed === false
      ? `Tu tarifa ${fare} no tiene reembolso.`
      : refund.allowed && refund.penalty
        ? isZero(refund.penalty)
          ? "Con reembolso total."
          : `Reembolso con cargo de ${formatPenalty(refund.penalty)}.`
        : "Consulta las condiciones con la aerolínea.";
  const rows: Record<string, ManageRow> = {
    change: { key: "change", title: "Cambiar vuelo", detail: changeDetail, icon: "⇄" },
    cancel: { key: "cancel", title: "Cancelar reserva", detail: cancelDetail, icon: "✕" },
    update: {
      key: "update",
      title: "Actualizar datos de contacto",
      detail: "Email y teléfono del pasajero.",
      icon: "✎",
    },
  };
  // The design's order, whatever order the provider lists them in.
  return (["change", "cancel", "update"] as const)
    .filter((key) => order.available_actions.includes(key))
    .map((key) => rows[key] as ManageRow);
}

/** Date of an instant in the browser's time zone: "mar 27 oct 2026". */
export function localDate(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return formatDate(`${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`);
}

export interface FailureContent {
  title: string;
  body: string;
  secondary?: { label: string; to: "checkout" | "results" };
}

/** What state 5 says for each `failure_code` (design board "Confirmación · no se pudo reservar"). */
export function failureContent(
  code: FailureCode | null | undefined,
  status: Booking["status"],
): FailureContent {
  if (status === "cancelled") {
    return {
      title: "No aceptaste el precio nuevo de la aerolínea.",
      body: "La reserva se canceló sin ningún cobro. En «Tu viaje» puedes actualizar el precio o elegir otra tarifa.",
    };
  }
  switch (code) {
    case "offer_expired":
      return {
        title: "La oferta venció antes de que la aerolínea la confirmara.",
        body: "Los precios se mantienen 30 minutos. En «Tu viaje» puedes actualizar el precio de este vuelo y volver a intentar.",
      };
    case "offer_unavailable":
      return {
        title: "La aerolínea ya no tiene lugar con esta tarifa.",
        body: "Pasa cuando se agotan los asientos a ese precio mientras se completa la compra. Puedes elegir otra tarifa del mismo vuelo u otro vuelo.",
        secondary: { label: "Buscar otro vuelo", to: "results" },
      };
    case "payment_declined":
      return {
        title: "La tarjeta fue rechazada.",
        body: "El emisor no autorizó el pago. Revisa los datos de la tarjeta o prueba con otra. La tarifa puede cambiar si pasa mucho tiempo.",
        secondary: { label: "Probar con otra tarjeta", to: "checkout" },
      };
    case "provider_rejected":
    case "passenger_rejected":
      return {
        title: "La aerolínea rechazó los datos del pasajero.",
        body: "Revisa que el nombre, el apellido y la fecha de nacimiento coincidan exactamente con el documento de viaje.",
        secondary: { label: "Revisar datos del pasajero", to: "checkout" },
      };
    default:
      return {
        title: "La aerolínea no respondió a tiempo.",
        body: "Suele ser algo pasajero. Espera unos minutos y vuelve a intentar desde «Tu viaje».",
      };
  }
}

/** After this long without an answer from the airline, the traveler is told it's taking longer. */
export const SLOW_BOOKING_MS = 60_000;

/**
 * Whether a booking has been waiting for the airline longer than usual.
 *
 * @param createdAt When the booking was created (UTC, from the API).
 * @param now Current time in ms.
 */
export function isTakingLong(createdAt: string, now: number): boolean {
  return now - new Date(createdAt).getTime() >= SLOW_BOOKING_MS;
}
