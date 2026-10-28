import { describe, expect, it } from "vitest";
import { todayIso } from "./dates";

describe("todayIso", () => {
  it("is the traveler's local calendar day, not the UTC one", () => {
    // 23:59 local is still that day, whatever the time zone of the test run.
    expect(todayIso(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
    expect(todayIso(new Date(2026, 0, 5, 0, 1).getTime())).toBe("2026-01-05");
  });

  it("pads month and day", () => {
    expect(todayIso(new Date(2026, 8, 3, 12))).toBe("2026-09-03");
  });
});
