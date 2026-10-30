import { describe, expect, it } from "vitest";
import { deviceKind, lastUse, signedInOn } from "./logic";

describe("connected devices", () => {
  it("picks the icon of each device", () => {
    expect(deviceKind("Chrome en Windows")).toBe("computer");
    expect(deviceKind("Safari en iPhone")).toBe("phone");
    expect(deviceKind("App en Pixel 8")).toBe("app");
  });

  it("says when each device was last used", () => {
    const now = Date.parse("2026-10-30T12:00:00Z");
    expect(lastUse("2026-10-30T11:00:00Z", true, now)).toBe("Ahora");
    expect(lastUse("2026-10-30T11:55:00Z", false, now)).toBe("Hace 5 min");
    expect(lastUse("2026-10-30T09:00:00Z", false, now)).toBe("Hace 3 h");
  });
});

describe("sign-in date", () => {
  it("reads like the board: «12 oct 2026»", () => {
    expect(signedInOn("2026-10-12T15:00:00Z")).toBe("12 oct 2026");
  });
});
