import { describe, expect, it } from "vitest";
import { EXPIRY_WARNING_MS, expiryOf } from "./useExpiry";

const at = Date.parse("2026-10-23T21:00:00Z");

describe("expiryOf", () => {
  it("is neutral with more than 5 minutes left", () => {
    expect(expiryOf("2026-10-23T21:10:00Z", at)).toEqual({
      remaining: 10 * 60_000,
      expired: false,
      warning: false,
    });
  });

  it("warns with less than 5 minutes left", () => {
    const expiry = expiryOf(new Date(at + EXPIRY_WARNING_MS - 1).toISOString(), at);
    expect(expiry).toMatchObject({ expired: false, warning: true });
  });

  it("is expired at the deadline, and still counts as a warning", () => {
    expect(expiryOf("2026-10-23T21:00:00Z", at)).toMatchObject({
      remaining: 0,
      expired: true,
      warning: true,
    });
  });

  it("treats a missing date as expired", () => {
    expect(expiryOf(undefined, at).expired).toBe(true);
  });
});
