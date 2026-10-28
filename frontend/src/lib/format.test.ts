import { describe, expect, it } from "vitest";
import {
  dayOffset,
  formatDate,
  formatDuration,
  formatMoney,
  formatPassengers,
  formatRemaining,
  formatTime,
  formatTotal,
  formatUtcDateTime,
  utcTime,
} from "./format";

describe("format", () => {
  it("shows money in its own currency, with Spanish separators", () => {
    expect(formatMoney({ amount: "402.74", currency: "USD" })).toBe("USD 402,74");
    expect(formatMoney({ amount: "6146.64", currency: "USD" })).toBe("USD 6.146,64");
    expect(formatMoney({ amount: "300", currency: "GBP" })).toBe("GBP 300,00");
  });

  it("formats durations", () => {
    expect(formatDuration(760)).toBe("12 h 40 min");
    expect(formatDuration(780)).toBe("13 h");
    expect(formatDuration(55)).toBe("55 min");
    expect(formatDuration(null)).toBe("Sin dato");
  });

  it("reads flight times as local text, without shifting them to the browser's zone", () => {
    expect(formatTime("2026-12-15T09:00:00")).toBe("09:00");
    expect(dayOffset("2026-12-15T22:30:00", "2026-12-16T06:10:00")).toBe(1);
    expect(dayOffset("2026-12-15T09:00:00", "2026-12-15T16:40:00")).toBe(0);
  });

  it("formats dates in Spanish", () => {
    expect(formatDate("2026-12-15")).toBe("mar 15 dic 2026");
    expect(formatDate("2026-12-15", { year: false, longWeekday: true })).toBe("martes, 15 dic");
  });

  it("formats remaining time and passengers", () => {
    expect(formatRemaining(24 * 60_000 + 5_000)).toBe("24 min");
    expect(formatRemaining(45_000)).toBe("45 s");
    expect(formatRemaining(0)).toBe("vencido");
    expect(formatPassengers(2, 1)).toBe("2 adultos · 1 menor");
  });
});

describe("booking formats", () => {
  it("puts the currency after the amount", () => {
    expect(formatTotal({ amount: "524.44", currency: "USD" })).toBe("524,44 USD");
  });

  it("shows an instant in UTC", () => {
    expect(formatUtcDateTime("2026-10-27T14:00:21Z")).toBe("27 oct 2026 14:00 UTC");
  });
});

describe("utcTime", () => {
  it("reads the time in UTC", () => {
    expect(utcTime("2026-10-23T21:26:50.636757Z")).toBe("21:26");
  });
});
