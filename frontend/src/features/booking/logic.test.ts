import { describe, expect, it } from "vitest";
import type { Booking } from "@/api/client";
import { fixtures } from "@/test/server";
import {
  bagsLine,
  daysLater,
  failureContent,
  includedItems,
  isTakingLong,
  manageRows,
  type Order,
  passengerName,
  sameIncluded,
  sliceDate,
} from "./logic";

const roundTrip = fixtures.bookings.confirmedRoundTrip;
const order = roundTrip.order as Order;

function withOrder(change: (order: Order) => void): Order {
  const copy = structuredClone(order);
  change(copy);
  return copy;
}

describe("confirmation rules", () => {
  it("writes the title before the name, as the airline got it", () => {
    expect(passengerName(roundTrip)).toBe("Sr. PEPE PEREZ");
    expect(
      passengerName({ ...roundTrip, passenger: { ...roundTrip.passenger, title: "ms" } } as Booking),
    ).toBe("Sra./Srta. PEPE PEREZ");
  });

  it("dates each slice by its first departure, as text", () => {
    expect(order.slices.map(sliceDate)).toEqual(["2026-11-10", "2026-11-15"]);
  });

  it("marks arrivals on a later day", () => {
    expect(daysLater("2026-12-15T22:10:00", "2026-12-16T06:05:00")).toBe(1);
    expect(daysLater("2026-11-10T06:58:00", "2026-11-10T07:55:00")).toBe(0);
  });

  it("lists what the fare includes, with «Sin dato» when unreported", () => {
    const items = includedItems(order.slices[0] as Order["slices"][number], order);

    expect(items.map((i) => [i.label, i.value])).toEqual([
      ["Equipaje de mano", "✓ 1 incluido"],
      ["Maleta de bodega", "✓ 1 incluida"],
      ["Cambios", "✗ No permite"],
      ["Reembolso", "✗ No permite"],
      ["Selección de asiento", "Sin dato"],
      ["Embarque prioritario", "Sin dato"],
    ]);
    expect(sameIncluded(order)).toBe(true);
  });

  it("shows it per slice when the slices differ", () => {
    const different = withOrder((o) => {
      for (const p of o.slices[1]?.segments[0]?.passengers ?? []) p.baggage.checked = 0;
    });

    expect(sameIncluded(different)).toBe(false);
  });

  it("describes the bags of a flight, never assuming", () => {
    expect(bagsLine({ carryOn: 1, checked: 1 }).text).toBe("✓ 1 de mano · ✓ 1 maleta");
    expect(bagsLine({ carryOn: 1, checked: 0 }).text).toBe("✓ 1 de mano · ✗ Maleta no incluida");
    expect(bagsLine({ carryOn: null, checked: null }).text).toBe("Equipaje: Sin dato");
  });

  it("explains each action the airline allows with the fare's conditions", () => {
    expect(manageRows(order).map((r) => [r.title, r.detail])).toEqual([
      ["Cambiar vuelo", "Tu tarifa Basic no permite cambios."],
      ["Cancelar reserva", "Tu tarifa Basic no tiene reembolso."],
      ["Actualizar datos de contacto", "Email y teléfono del pasajero."],
    ]);
    expect(manageRows(withOrder((o) => (o.available_actions = [])))).toEqual([]);
  });

  it("says a booking is taking long only after a minute", () => {
    const created = "2026-10-28T12:00:00Z";
    const at = (seconds: number) => new Date(created).getTime() + seconds * 1000;

    expect(isTakingLong(created, at(59))).toBe(false);
    expect(isTakingLong(created, at(60))).toBe(true);
  });

  it("explains each failure and what to do next", () => {
    expect(failureContent("payment_declined", "failed").secondary?.to).toBe("checkout");
    expect(failureContent("offer_unavailable", "failed").secondary?.to).toBe("results");
    expect(failureContent("provider_unavailable", "failed").secondary).toBeUndefined();
  });
});
