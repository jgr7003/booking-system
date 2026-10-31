import { describe, expect, it } from "vitest";
import {
  checkoutItemKey,
  comesFromCheckout,
  firstName,
  initials,
  rememberProviderSignIn,
  resendWait,
  safeReturnTo,
  takeProviderSignIn,
} from "./flow";

describe("sign-in flow", () => {
  it("only goes back to paths of this app", () => {
    expect(safeReturnTo("/checkout/duffel:abc")).toBe("/checkout/duffel:abc");
    expect(safeReturnTo("https://malo.test")).toBeNull();
    expect(safeReturnTo("//malo.test")).toBeNull();
    expect(safeReturnTo("/login?return_to=/trip")).toBeNull();
    expect(safeReturnTo(undefined)).toBeNull();
  });

  it("tells the checkout and its trip item", () => {
    expect(comesFromCheckout("/checkout/duffel%3Aabc")).toBe(true);
    expect(checkoutItemKey("/checkout/duffel%3Aabc")).toBe("duffel:abc");
    expect(comesFromCheckout("/trip")).toBe(false);
  });

  it("remembers a provider sign in by its state, once", () => {
    rememberProviderSignIn("https://idp.test/auth?state=s1&code_challenge=x", {
      provider: "google",
      providerName: "Google",
      returnTo: "/trip",
    });

    expect(takeProviderSignIn("s1")).toEqual({
      provider: "google",
      providerName: "Google",
      returnTo: "/trip",
    });
    expect(takeProviderSignIn("s1")).toBeNull();
  });

  it("waits longer before each resend", () => {
    expect([0, 1, 2, 5].map(resendWait)).toEqual([60, 120, 240, 480]);
  });

  it("builds the initials and first name of the account button", () => {
    expect(initials("Pepe Perez")).toBe("PP");
    expect(initials("ana maría de la Fuente")).toBe("AF");
    expect(firstName("Pepe Perez")).toBe("Pepe");
  });
});
