import { describe, expect, it } from "vitest";
import type { FlightSegment } from "@/api/client";
import { fixtures } from "@/test/server";
import { amenityRows, benefitCell, penaltyCell } from "./logic";

const segment = fixtures.search.flights[0]?.slices[0]?.segments[0] as FlightSegment;

function withAmenities(amenities: NonNullable<FlightSegment["cabin"]>["amenities"]): FlightSegment {
  return { ...segment, cabin: { cabin_class: "economy", cabin_name: "Economy", amenities } };
}

describe("amenityRows", () => {
  it("says the airline didn't inform them when there are none", () => {
    expect(amenityRows({ ...segment, cabin: null })).toEqual([
      { k: "Comodidades", cell: { label: "Sin informar", tone: "na" } },
    ]);
  });

  it("describes wifi, power and seat", () => {
    const rows = amenityRows(withAmenities({ wifi: "paid", power: true, seat_pitch: "30", legroom: "more" }));
    expect(rows).toEqual([
      { k: "Wi-Fi", cell: { label: "Pago", tone: "warn" } },
      { k: "Enchufe", cell: { label: "Sí", tone: "ok" } },
      { k: "Asiento", cell: { label: "30″ · más espacio", tone: "ok" } },
    ]);
  });

  it("keeps a missing value as «Sin dato», not as a no", () => {
    const rows = amenityRows(withAmenities({ wifi: null, power: null, seat_pitch: "30", legroom: null }));
    expect(rows.map((r) => r.cell)).toEqual([
      { label: "Sin dato", tone: "na" },
      { label: "Sin dato", tone: "na" },
      { label: "30″ · espacio sin dato", tone: "na" },
    ]);
  });
});

describe("penaltyCell", () => {
  it("prefixes a fee with «Con cargo»", () => {
    const cell = penaltyCell({ allowed: true, penalty: { amount: "300.00", currency: "GBP" } });
    expect(cell.tone).toBe("warn");
    expect(cell.label).toMatch(/^Con cargo · /);
  });

  it("leaves free and forbidden changes as they are", () => {
    expect(penaltyCell({ allowed: true, penalty: { amount: "0.00", currency: "GBP" } })).toEqual({
      label: "Gratis",
      tone: "ok",
    });
    expect(penaltyCell({ allowed: false, penalty: null })).toEqual({ label: "No permite", tone: "bad" });
  });
});

describe("benefitCell", () => {
  it("tells true, false and unknown apart", () => {
    expect(benefitCell(true, "Incluido")).toEqual({ label: "Incluido", tone: "ok" });
    expect(benefitCell(false, "Incluido")).toEqual({ label: "No incluido", tone: "bad" });
    expect(benefitCell(null, "Incluido")).toEqual({ label: "Sin dato", tone: "na" });
  });
});
