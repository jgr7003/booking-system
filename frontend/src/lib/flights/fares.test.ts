import { describe, expect, it } from "vitest";
import type { Fare, Flight } from "@/api/client";
import { fixtures } from "@/test/server";
import { bagCell, conditionCell, fareCarryOn, fareCheckedBags, fareName } from "./fares";

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
