import { describe, expect, it } from "vitest";
import { flightSearchSchema, passengersError, searchErrors, toCriteria } from "./search";

describe("search params", () => {
  it("builds the API criteria", () => {
    expect(
      toCriteria({
        from: "LHR",
        to: "JFK",
        depart: "2026-12-15",
        ret: "2026-12-22",
        adults: 2,
        children: [8],
        direct: true,
      }),
    ).toEqual({
      origin: "LHR",
      destination: "JFK",
      departure_date: "2026-12-15",
      return_date: "2026-12-22",
      passengers: { adults: 2, children_ages: [8] },
      cabin_class: null,
      max_connections: 0,
    });
  });

  it("a broken URL drops the bad fields instead of failing", () => {
    expect(flightSearchSchema.parse({ from: "LHR", to: "new york", depart: "tomorrow", adults: 20 })).toEqual(
      {
        from: "LHR",
        to: undefined,
        depart: undefined,
        ret: undefined,
        adults: undefined,
        children: undefined,
        cabin: undefined,
        direct: undefined,
      },
    );
  });

  it("validates passengers like the backend", () => {
    expect(passengersError(1, [0])).toBeNull();
    expect(passengersError(1, [0, 1])).toMatch(/adulto distinto/);
    expect(passengersError(5, [3, 4, 5, 6, 7])).toMatch(/9 pasajeros/);
  });

  it("validates route and dates", () => {
    const errors = searchErrors(
      { from: "LHR", to: "LHR", depart: "2026-10-01", ret: "2026-09-01" },
      "2026-10-26",
    );
    expect(Object.keys(errors).sort()).toEqual(["depart", "ret", "to"]);
  });
});
