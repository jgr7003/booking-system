import { describe, expect, it } from "vitest";
import { fixtures } from "@/test/server";
import { conditionsLine, totalsByCurrency } from "./logic";
import { makeTripItem, type TripItem } from "./store";

function itemWith(conditions: TripItem["fare"]["conditions"]): TripItem {
  const flight = fixtures.search.flights[0];
  const fare = flight?.fares[0];
  if (!flight || !fare) throw new Error("fixture without flights");
  const item = makeTripItem(flight, fare, { from: "LHR", to: "JFK", depart: "2026-12-15" }, "orq_1");
  return { ...item, fare: { ...fare, conditions } };
}

const free = { allowed: true, penalty: { amount: "0.00", currency: "USD" } };
const fee = { allowed: true, penalty: { amount: "40.00", currency: "USD" } };
const no = { allowed: false, penalty: null };

describe("conditionsLine", () => {
  it("is green when changing and refunding are free", () => {
    expect(conditionsLine(itemWith({ change: free, refund: free }))).toEqual({
      text: "Cambio gratis · reembolso gratis",
      tone: "ok",
    });
  });

  it("names the fees and is amber when there are any", () => {
    const line = conditionsLine(itemWith({ change: fee, refund: no }));
    expect(line.text).toMatch(/^Cambio 40 USD · sin reembolso$/);
    expect(line.tone).toBe("warn");
  });

  it("is red when the fare can't be changed", () => {
    expect(conditionsLine(itemWith({ change: no, refund: no }))).toEqual({
      text: "Cambio: no permite · sin reembolso",
      tone: "bad",
    });
  });
});

describe("totalsByCurrency", () => {
  it("adds amounts in cents, without floating point drift", () => {
    expect(
      totalsByCurrency([
        { amount: "0.10", currency: "USD" },
        { amount: "0.20", currency: "USD" },
      ]),
    ).toEqual([{ amount: "0.30", currency: "USD" }]);
  });

  it("never converts between currencies", () => {
    expect(
      totalsByCurrency([
        { amount: "100.00", currency: "USD" },
        { amount: "50.00", currency: "EUR" },
        { amount: "1.50", currency: "USD" },
      ]),
    ).toEqual([
      { amount: "101.50", currency: "USD" },
      { amount: "50.00", currency: "EUR" },
    ]);
  });

  it("is empty for an empty trip", () => {
    expect(totalsByCurrency([])).toEqual([]);
  });
});
