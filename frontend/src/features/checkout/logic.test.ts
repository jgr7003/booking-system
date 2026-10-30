import { describe, expect, it } from "vitest";
import { fixtures } from "@/test/server";
import {
  accountPassenger,
  accountPhone,
  accountTraveller,
  ageOn,
  airlineNameLength,
  bagsSummary,
  buildBookingRequest,
  type CheckoutValues,
  checkoutSchema,
  conditionsSummary,
  EMPTY_VALUES,
  isoDateOf,
  isTransliterated,
  isValidCardExpiry,
  isValidCardNumber,
  paymentToken,
  toAirlineName,
  toE164,
} from "./logic";

const VALID: CheckoutValues = {
  ...EMPTY_VALUES,
  title: "ms",
  givenName: "Ana",
  familyName: "Muñoz",
  gender: "f",
  birthDay: "20",
  birthMonth: "5",
  birthYear: "1990",
  email: "ana.prueba@example.com",
  phoneCountry: "AR",
  phoneNumber: "9 11 1234-5678",
  cardNumber: "4242 4242 4242 4242",
  cardHolder: "ANA MUNOZ",
  cardExpiry: "12/30",
  cardCode: "123",
  acceptConditions: true,
};

function errorsOf(values: CheckoutValues, { requiresPassport = false, departureDate = "2026-12-15" } = {}) {
  const result = checkoutSchema({ departureDate, requiresPassport, today: "2026-10-27" }).safeParse(values);
  return result.success ? {} : Object.fromEntries(result.error.issues.map((i) => [i.path[0], i.message]));
}

describe("airline names", () => {
  it.each([
    ["Muñoz", "MUNOZ"],
    ["José María", "JOSE MARIA"],
    ["  Ana   Lía ", "ANA LIA"],
    ["O’Brien", "O'BRIEN"],
    ["Straße", "STRASSE"],
  ])("transliterates %s as %s, like the backend", (typed, sent) => {
    expect(toAirlineName(typed)).toBe(sent);
  });

  it.each(["Ana2", "李", "Ana_Lía", "-Ana"])("rejects %s", (name) => {
    expect(toAirlineName(name)).toBeNull();
  });

  it("warns only when the airline gets something other than the typed name in capitals", () => {
    expect(isTransliterated("Muñoz")).toBe(true);
    expect(isTransliterated("Prueba")).toBe(false);
  });

  it("counts the transliterated length", () => {
    expect(airlineNameLength("Ana", "Straße")).toBe(3 + 7);
  });
});

describe("dates", () => {
  it("builds real dates only", () => {
    expect(isoDateOf("20", "5", "1990")).toBe("1990-05-20");
    expect(isoDateOf("31", "2", "1990")).toBeNull();
    expect(isoDateOf("1", "1", "90")).toBeNull();
  });

  it("calculates the age on the day of the flight", () => {
    expect(ageOn("2008-12-15", "2026-12-15")).toBe(18);
    expect(ageOn("2008-12-16", "2026-12-15")).toBe(17);
  });
});

describe("phone and card", () => {
  it("formats the phone in E.164", () => {
    expect(toE164("AR", "9 11 1234-5678")).toBe("+5491112345678");
    expect(toE164("AR", "123")).toBeNull();
  });

  it("checks the card number and expiry", () => {
    expect(isValidCardNumber("4242 4242 4242 4242")).toBe(true);
    expect(isValidCardNumber("4242 4242 4242 4241")).toBe(false);
    expect(isValidCardExpiry("10/26", "2026-10-27")).toBe(true);
    expect(isValidCardExpiry("09/26", "2026-10-27")).toBe(false);
    expect(isValidCardExpiry("13/30", "2026-10-27")).toBe(false);
  });

  it("sends a token with the last 4 digits, never the card number", () => {
    expect(paymentToken("4000 0000 0000 0002")).toBe("tok_fake_0002");
  });
});

describe("checkout form", () => {
  it("accepts a valid adult", () => {
    expect(errorsOf(VALID)).toEqual({});
  });

  it("shows every problem at once", () => {
    const errors = errorsOf(EMPTY_VALUES);

    expect(Object.keys(errors).sort()).toEqual(
      [
        "acceptConditions",
        "birthDay",
        "cardCode",
        "cardExpiry",
        "cardHolder",
        "cardNumber",
        "email",
        "familyName",
        "gender",
        "givenName",
        "phoneNumber",
        "title",
      ].sort(),
    );
  });

  it("rejects names the airline can't take and more than 40 characters", () => {
    expect(errorsOf({ ...VALID, familyName: "Prueba2" }).familyName).toMatch(/Usa solo letras/);
    expect(errorsOf({ ...VALID, givenName: "A".repeat(20), familyName: "B".repeat(21) }).familyName).toMatch(
      /40/,
    );
  });

  it("requires an adult on the day of the flight", () => {
    const minor = { ...VALID, birthDay: "16", birthMonth: "12", birthYear: "2008" };

    expect(errorsOf(minor).birthDay).toMatch(/18 años o más/);
    expect(errorsOf(minor, { departureDate: "2026-12-16" }).birthDay).toBeUndefined();
  });

  it("asks for a valid passport only when the fare requires it", () => {
    expect(errorsOf(VALID).passportNumber).toBeUndefined();
    const errors = errorsOf(VALID, { requiresPassport: true });
    expect(errors.passportNumber).toBeDefined();
    expect(errors.passportExpiry).toBeDefined();
    expect(
      errorsOf(
        { ...VALID, passportNumber: "AB1234567", passportExpiry: "01/01/2032" },
        { requiresPassport: true },
      ),
    ).toEqual({});
  });
});

describe("booking request", () => {
  it("has the fare, the expected price, the passenger in E.164 and the card token", () => {
    const fare = fixtures.search.flights[0]?.fares[0];
    if (!fare) throw new Error("fixture without fares");

    const body = buildBookingRequest(VALID, fare);

    expect(body.offer_id).toBe(fare.offer_id);
    expect(body.expected_price).toEqual(fare.price.total);
    expect(body.passenger).toEqual({
      title: "ms",
      traveller: {
        given_name: "Ana",
        family_name: "Muñoz",
        born_on: "1990-05-20",
        gender: "f",
        email: "ana.prueba@example.com",
        phone_number: "+5491112345678",
        identity_documents: [],
      },
      is_account_holder: false,
    });
    expect(body.payment_token).toBe("tok_fake_4242");
    expect(JSON.stringify(body)).not.toContain("4242 4242");
  });

  it("says when the signed-in user is the one who travels", () => {
    const fare = fixtures.search.flights[0]?.fares[0];
    if (!fare) throw new Error("fixture without fares");

    expect(buildBookingRequest(VALID, fare, true).passenger.is_account_holder).toBe(true);
  });
});

describe("summary texts", () => {
  const fareOf = (name: string) => {
    const fare = fixtures.search.flights
      .flatMap((f) => f.fares)
      .find((f) => f.slices[0]?.fare_brand === name);
    if (!fare) throw new Error(`no ${name} fare in the fixture`);
    return fare;
  };

  it("describes change and refund like the design", () => {
    expect(conditionsSummary(fareOf("Economy Light"))).toMatch(
      /^(sin cambios|cambio con cargo de [\d,.]+ \w{3})/,
    );
  });

  it("never assumes an unreported cabin bag", () => {
    expect(bagsSummary(fareOf("Economy Impact"))).toContain("mano: sin dato");
  });
});

describe("passenger from the account", () => {
  it("fills the names as the airline takes them, and the email", () => {
    expect(accountPassenger({ name: "José Muñoz de la Peña", email: "jose@ejemplo.com" })).toEqual({
      givenName: "JOSE",
      familyName: "MUNOZ DE LA PENA",
      email: "jose@ejemplo.com",
    });
  });

  it("splits the phone of the account into country and national number", () => {
    expect(accountPhone("+573105826464")).toEqual({ phoneCountry: "CO", phoneNumber: "3105826464" });
    expect(accountPhone("+5491112345678")).toEqual({ phoneCountry: "AR", phoneNumber: "91112345678" });
  });

  it("leaves the phone empty when the account's can't be read", () => {
    expect(accountPhone("12345")).toBeNull();
  });

  it("fills title, date of birth and gender from the last booking for themselves", () => {
    expect(accountTraveller({ title: "mr", born_on: "1990-08-23", gender: "m" })).toEqual({
      title: "mr",
      gender: "m",
      birthDay: "23",
      birthMonth: "08",
      birthYear: "1990",
    });
  });
});
