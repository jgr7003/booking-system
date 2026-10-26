import { describe, expect, it } from "vitest";
import type { Fare, Flight } from "@/api/client";
import { fixtures } from "@/test/server";
import {
  applyFilters,
  bagCell,
  conditionCell,
  fareCarryOn,
  fareCheckedBags,
  fareName,
  flightTag,
  groupByOutbound,
  isRoundTrip,
  outboundKeyOf,
  relaxSuggestions,
  returnView,
  sortFlights,
  stopMarkers,
} from "./logic";

const flights = fixtures.search.flights;
const byNumbers = (numbers: string) =>
  flights.find((f) => f.slices[0]?.segments.map((s) => s.flight_number).join("+") === numbers) as Flight;
const lx317 = byNumbers("0317+0014"); // Lufthansa, flown by SWISS via ZRH, 5 fares
const fareNamed = (flight: Flight, name: string) => flight.fares.find((f) => fareName(f) === name) as Fare;

describe("fare values", () => {
  it("unknown cabin bag is «Sin dato», never 0", () => {
    const impact = fareNamed(lx317, "Economy Impact");
    expect(fareCarryOn(impact)).toBeNull();
    expect(bagCell(fareCarryOn(impact), "carry_on")).toEqual({ label: "Sin dato", tone: "na" });
    expect(bagCell(fareCheckedBags(impact), "checked")).toEqual({ label: "1 incluida", tone: "ok" });
  });

  it("explicit 0 is «No incluida»", () => {
    const light = fareNamed(lx317, "Economy Light");
    expect(bagCell(fareCheckedBags(light), "checked")).toEqual({ label: "No incluida", tone: "bad" });
  });

  it("change and refund keep the penalty currency", () => {
    const light = fareNamed(lx317, "Economy Light");
    expect(conditionCell(light.conditions.change)).toEqual({ label: "300 GBP", tone: "warn" });
    expect(conditionCell(light.conditions.refund)).toEqual({ label: "No permite", tone: "bad" });
    expect(conditionCell({ allowed: true, penalty: { amount: "0.00", currency: "GBP" } })).toEqual({
      label: "Gratis",
      tone: "ok",
    });
    expect(conditionCell({ allowed: null })).toEqual({ label: "Sin dato", tone: "na" });
  });
});

describe("filters and sort", () => {
  it("«Con valija» only keeps fares with a reported checked bag", () => {
    const result = applyFilters(flights, { bag: true });
    const filtered = result.find((f) => f.key === lx317.key) as Flight;

    expect(filtered.fares.map(fareName)).not.toContain("Economy Light");
    expect(filtered.fares.every((f) => (fareCheckedBags(f) ?? 0) >= 1)).toBe(true);
    expect(filtered.lowest_price).toEqual(filtered.fares[0]?.price.total);
  });

  it("direct flights", () => {
    expect(
      applyFilters(flights, { direct: true })
        .map((f) => f.owner.code)
        .sort(),
    ).toEqual(["AA", "BA", "IB", "ZZ"]);
  });

  it("suggests which filter to drop when nothing matches", () => {
    const filters = { direct: true, refund: true, time: "evening" as const };
    expect(applyFilters(flights, filters)).toHaveLength(0);

    const suggestions = relaxSuggestions(flights, filters);
    expect(suggestions.map((s) => s.filter)).toContain("time");
    expect(suggestions.every((s) => s.count > 0)).toBe(true);
  });

  it("sorts by price, duration and departure", () => {
    const price = sortFlights(flights, "price").map((f) => Number(f.lowest_price.amount));
    expect(price).toEqual([...price].sort((a, b) => a - b));
    const duration = sortFlights(flights, "duration");
    expect(duration[0]?.slices[0]?.stops).toBe(0);
    const departure = sortFlights(flights, "departure").map(
      (f) => f.slices[0]?.segments[0]?.departing_at ?? "",
    );
    expect(departure).toEqual([...departure].sort());
  });
});

describe("card details", () => {
  it("places the layover on the timeline by real time", () => {
    const [zrh] = stopMarkers(lx317.slices[0] as Flight["slices"][number]);
    // 1 h 55 flight + 1 h 15 layover + 9 h 30 flight = 12 h 40.
    expect(zrh?.airport).toBe("ZRH");
    expect(zrh?.minutes).toBe(75);
    expect(zrh?.short).toBe(false);
    expect(zrh?.left).toBeCloseTo((115 / 760) * 100);
  });

  it("tags the cheapest flight, short connections and the test airline", () => {
    const sorted = sortFlights(flights, "price");
    expect(flightTag(sorted[0] as Flight, flights)).toEqual({ label: "Más barato", tone: "ok" });

    const shortOne = flights.find((f) =>
      stopMarkers(f.slices[0] as Flight["slices"][number]).some((m) => m.short),
    );
    expect(flightTag(shortOne as Flight, flights)?.tone).toBe("warn");

    const duffelAirways = flights.find((f) => f.owner.code === "ZZ") as Flight;
    expect(flightTag(duffelAirways, flights)?.label).toBe("Aerolínea de prueba");
  });
});

describe("round trips in two steps", () => {
  const combinations = fixtures.roundTrip.flights;

  it("only round trips are shown in two steps", () => {
    expect(isRoundTrip(combinations)).toBe(true);
    expect(isRoundTrip(flights)).toBe(false);
    expect(isRoundTrip([])).toBe(false);
  });

  it("lists each outbound once, with its returns", () => {
    const outbounds = groupByOutbound(combinations);

    expect(outbounds).toHaveLength(7);
    expect(outbounds.reduce((n, o) => n + o.returns.length, 0)).toBe(combinations.length);
    expect(outbounds.map((o) => o.returns.length).sort((a, b) => b - a)).toEqual([17, 17, 17, 1, 1, 1, 1]);
    for (const outbound of outbounds) {
      expect(outbound.flight.slices).toHaveLength(1);
      expect(outbound.returns.every((r) => outboundKeyOf(r) === outbound.key)).toBe(true);
      const cheapest = Math.min(...outbound.returns.map((r) => Number(r.lowest_price.amount)));
      expect(Number(outbound.flight.lowest_price.amount)).toBe(cheapest);
    }
  });

  it("keeps the order of the list it receives", () => {
    const sorted = sortFlights(combinations, "price");
    const [first] = groupByOutbound(sorted);

    expect(first?.returns[0]).toBe(sorted[0]);
  });

  it("a return card keeps the combination's key", () => {
    const combination = combinations[0] as Flight;
    const view = returnView(combination);

    expect(view.key).toBe(combination.key);
    expect(view.slices).toEqual([combination.slices[1]]);
  });
});
