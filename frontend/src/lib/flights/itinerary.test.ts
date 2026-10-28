import { describe, expect, it } from "vitest";
import type { Flight } from "@/api/client";
import { fixtures } from "@/test/server";
import { stopMarkers } from "./itinerary";

const flights = fixtures.search.flights;
const byNumbers = (numbers: string) =>
  flights.find((f) => f.slices[0]?.segments.map((s) => s.flight_number).join("+") === numbers) as Flight;
const lx317 = byNumbers("0317+0014"); // Lufthansa, flown by SWISS via ZRH, 5 fares

describe("stopMarkers", () => {
  it("places the layover on the timeline by real time", () => {
    const [zrh] = stopMarkers(lx317.slices[0] as Flight["slices"][number]);
    // 1 h 55 flight + 1 h 15 layover + 9 h 30 flight = 12 h 40.
    expect(zrh?.airport).toBe("ZRH");
    expect(zrh?.minutes).toBe(75);
    expect(zrh?.short).toBe(false);
    expect(zrh?.left).toBeCloseTo((115 / 760) * 100);
  });
});
