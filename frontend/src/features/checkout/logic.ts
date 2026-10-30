import {
  type CountryCode,
  getCountries,
  getCountryCallingCode,
  parsePhoneNumberFromString,
} from "libphonenumber-js";
import { z } from "zod";
import type { BookingRequest, FailureCode, Fare, FareCondition, Flight, PassengerTitle } from "@/api/client";
import { fareCarryOn, fareCheckedBags } from "@/lib/flights/fares";
import { formatPenalty, isZero, LOCALE } from "@/lib/format";

/**
 * Rules of the passengers and payment form. They mirror the backend's (which has the last word)
 * so the traveler sees problems before sending.
 */

/** Airlines accept at most this many characters for the given and family names together. */
export const MAX_NAME_LENGTH = 40;

/** Passengers are adults from this age, on the day of the flight. */
export const ADULT_AGE = 18;

/** Country of the phone and passport selectors before the traveler picks one. */
export const DEFAULT_COUNTRY: CountryCode = "CO";

/** Titles in the order of the design, with their labels. */
export const TITLES: { value: PassengerTitle; label: string }[] = [
  { value: "mr", label: "Sr. (mr)" },
  { value: "mrs", label: "Sra. (mrs)" },
  { value: "ms", label: "Sra./Srta. (ms)" },
  { value: "miss", label: "Srta. (miss)" },
  { value: "dr", label: "Dr./Dra. (dr)" },
];

// Letters that don't decompose into an ASCII letter plus accents (same table as the backend).
const TRANSLITERATIONS: Record<string, string> = {
  ß: "SS",
  Æ: "AE",
  æ: "AE",
  Ø: "O",
  ø: "O",
  Œ: "OE",
  œ: "OE",
  Đ: "D",
  đ: "D",
  Ð: "D",
  ð: "D",
  Ł: "L",
  ł: "L",
  Þ: "TH",
  þ: "TH",
  ı: "I",
  "’": "'",
  "‘": "'",
};

const AIRLINE_NAME = /^[A-Z]+(?:[ '-][A-Z]+)*$/;

/**
 * A name as the airline gets it: upper-case ASCII letters, spaces, `-` and `'` ("Muñoz" → "MUNOZ").
 * `null` if it has characters that can't be transliterated (digits, other scripts...).
 */
export function toAirlineName(name: string): string | null {
  const replaced = [...name].map((c) => TRANSLITERATIONS[c] ?? c).join("");
  const plain = replaced
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toUpperCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
  return AIRLINE_NAME.test(plain) ? plain : null;
}

/** Characters both names take for the airline (what the "n / 40" counter shows). */
export function airlineNameLength(givenName: string, familyName: string): number {
  const length = (name: string) => (toAirlineName(name) ?? name.trim()).length;
  return length(givenName) + length(familyName);
}

/** Whether the airline gets the names differently than typed (beyond upper case): warn first. */
export function isTransliterated(name: string): boolean {
  const airline = toAirlineName(name);
  return airline !== null && airline !== name.trim().split(/\s+/).join(" ").toUpperCase();
}

/** "2008-12-15" if day, month and year make a real date; `null` otherwise. */
export function isoDateOf(day: string, month: string, year: string): string | null {
  if (!/^\d{1,2}$/.test(day) || !/^\d{1,2}$/.test(month) || !/^\d{4}$/.test(year)) return null;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (date.getUTCDate() !== Number(day) || date.getUTCMonth() !== Number(month) - 1) return null;
  return date.toISOString().slice(0, 10);
}

/** "15/12/2026" → "2026-12-15", or `null`. */
export function isoDateOfText(text: string): string | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text.trim());
  return match ? isoDateOf(match[1] ?? "", match[2] ?? "", match[3] ?? "") : null;
}

/** Age in whole years on a day (both "YYYY-MM-DD"). */
export function ageOn(bornOn: string, day: string): number {
  const [by, bm, bd] = bornOn.split("-").map(Number) as [number, number, number];
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  return y - by - (m < bm || (m === bm && d < bd) ? 1 : 0);
}

/** Local departure date of a flight: "2026-12-15" (read as text, never converted). */
export function departureDateOf(flight: Pick<Flight, "slices">): string {
  return flight.slices[0]?.segments[0]?.departing_at.slice(0, 10) ?? "";
}

/** The phone in E.164 ("+5491112345678"), or `null` if it isn't a valid number of that country. */
export function toE164(country: string, national: string): string | null {
  const phone = parsePhoneNumberFromString(national, country as CountryCode);
  return phone?.isValid() ? phone.number : null;
}

const regionNames = new Intl.DisplayNames([LOCALE], { type: "region" });

/** The calling code of a country for the phone hint, e.g. `CO` → `57`. */
export function callingCodeOf(country: string): string {
  return getCountryCallingCode(country as CountryCode);
}

/** Countries for the phone and passport selectors, sorted by name in Spanish. */
export function countries(): { code: CountryCode; name: string; callingCode: string }[] {
  return getCountries()
    .map((code) => ({ code, name: regionNames.of(code) ?? code, callingCode: getCountryCallingCode(code) }))
    .sort((a, b) => a.name.localeCompare(b.name, LOCALE));
}

/** Luhn checksum of a card number (spaces allowed). */
export function isValidCardNumber(number: string): boolean {
  const digits = number.replace(/\s/g, "");
  if (!/^\d{12,19}$/.test(digits)) return false;
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let digit = Number(digits[digits.length - 1 - i]);
    if (i % 2 === 1) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
  }
  return sum % 10 === 0;
}

/** Whether "MM/AA" is a valid expiry that hasn't passed by `today` ("YYYY-MM-DD"). */
export function isValidCardExpiry(text: string, today: string): boolean {
  const match = /^(\d{2})\/(\d{2})$/.exec(text.trim());
  if (!match) return false;
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  if (month < 1 || month > 12) return false;
  const [ty, tm] = today.split("-").map(Number) as [number, number];
  return year > ty || (year === ty && month >= tm);
}

/**
 * Token of the card for the API. The simulated gateway takes `tok_fake_<last 4 digits>`; the
 * card number and the code never leave the browser, as with a real gateway's tokenization.
 */
export function paymentToken(cardNumber: string): string {
  return `tok_fake_${cardNumber.replace(/\s/g, "").slice(-4)}`;
}

/** What the traveler fills in. Dates are typed as text, as in the design. */
export interface CheckoutValues {
  title: PassengerTitle | "";
  givenName: string;
  familyName: string;
  gender: "m" | "f" | "";
  birthDay: string;
  birthMonth: string;
  birthYear: string;
  email: string;
  phoneCountry: string;
  phoneNumber: string;
  passportNumber: string;
  passportCountry: string;
  passportExpiry: string;
  cardNumber: string;
  cardHolder: string;
  cardExpiry: string;
  cardCode: string;
  acceptConditions: boolean;
}

/** Fields kept in the draft if the offer expires or the page reloads: never the card. */
export type PassengerDraft = Omit<CheckoutValues, "cardNumber" | "cardHolder" | "cardExpiry" | "cardCode">;

export const EMPTY_VALUES: CheckoutValues = {
  title: "",
  givenName: "",
  familyName: "",
  gender: "",
  birthDay: "",
  birthMonth: "",
  birthYear: "",
  email: "",
  phoneCountry: DEFAULT_COUNTRY,
  phoneNumber: "",
  passportNumber: "",
  passportCountry: DEFAULT_COUNTRY,
  passportExpiry: "",
  cardNumber: "",
  cardHolder: "",
  cardExpiry: "",
  cardCode: "",
  acceptConditions: false,
};

/** The draft part of the values. */
export function draftOf(values: CheckoutValues): PassengerDraft {
  const { cardNumber: _n, cardHolder: _h, cardExpiry: _e, cardCode: _c, ...draft } = values;
  return draft;
}

// Loose on purpose (the backend uses the same shape): the address is confirmed by writing to it.
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const NAME_ERROR = "Usa solo letras, espacios, guion (-) o apóstrofo (').";

/**
 * Validation of the form for one fare.
 *
 * @param departureDate Local departure date: the traveler must be an adult on that day.
 * @param requiresPassport Whether the fare asks for a passport.
 * @param today "YYYY-MM-DD", to validate dates in the past or the future.
 */
export function checkoutSchema({
  departureDate,
  requiresPassport,
  today,
}: {
  departureDate: string;
  requiresPassport: boolean;
  today: string;
}) {
  // Every rule lives in one refinement over plain fields: Zod skips object refinements once a
  // field fails, and the traveler should see every problem at once.
  return z
    .object({
      title: z.enum(["", "mr", "ms", "mrs", "miss", "dr"]),
      givenName: z.string(),
      familyName: z.string(),
      gender: z.enum(["", "m", "f"]),
      birthDay: z.string(),
      birthMonth: z.string(),
      birthYear: z.string(),
      email: z.string(),
      phoneCountry: z.string(),
      phoneNumber: z.string(),
      passportNumber: z.string(),
      passportCountry: z.string(),
      passportExpiry: z.string(),
      cardNumber: z.string(),
      cardHolder: z.string(),
      cardExpiry: z.string(),
      cardCode: z.string(),
      acceptConditions: z.boolean(),
    })
    .superRefine((v, ctx) => {
      const issue = (path: keyof CheckoutValues, message: string) =>
        ctx.addIssue({ code: "custom", path: [path], message });

      if (!v.title) issue("title", "Elige el tratamiento.");
      if (!v.givenName.trim()) issue("givenName", "Escribe el nombre.");
      else if (toAirlineName(v.givenName) === null) issue("givenName", NAME_ERROR);
      if (!v.familyName.trim()) issue("familyName", "Escribe el apellido.");
      else if (toAirlineName(v.familyName) === null) issue("familyName", NAME_ERROR);
      else if (airlineNameLength(v.givenName, v.familyName) > MAX_NAME_LENGTH) {
        issue("familyName", `Nombre y apellido juntos no pueden superar los ${MAX_NAME_LENGTH} caracteres.`);
      }
      if (!v.gender) issue("gender", "Elige el género que figura en el documento.");

      const bornOn = isoDateOf(v.birthDay, v.birthMonth, v.birthYear);
      if (!bornOn || bornOn >= today) issue("birthDay", "Revisa la fecha de nacimiento.");
      else if (departureDate && ageOn(bornOn, departureDate) < ADULT_AGE) {
        issue("birthDay", `Un adulto debe tener ${ADULT_AGE} años o más el día del vuelo.`);
      }

      if (!EMAIL.test(v.email.trim()))
        issue("email", v.email.trim() ? "Revisa el email." : "Escribe el email.");
      if (!v.phoneNumber.trim()) issue("phoneNumber", "Escribe el teléfono.");
      else if (toE164(v.phoneCountry, v.phoneNumber) === null) {
        issue("phoneNumber", "Revisa el teléfono: no es un número válido de ese país.");
      }

      if (requiresPassport) {
        if (!/^[A-Za-z0-9 -]{1,20}$/.test(v.passportNumber.trim())) {
          issue("passportNumber", "Escribe el número de pasaporte.");
        }
        const expires = isoDateOfText(v.passportExpiry);
        if (!expires || expires <= today) {
          issue("passportExpiry", "Revisa el vencimiento: el pasaporte tiene que estar vigente.");
        }
      }

      if (!isValidCardNumber(v.cardNumber)) issue("cardNumber", "Revisa el número de tarjeta.");
      if (!v.cardHolder.trim()) issue("cardHolder", "Escribe el nombre del titular.");
      if (!isValidCardExpiry(v.cardExpiry, today)) issue("cardExpiry", "Revisa el vencimiento (MM/AA).");
      if (!/^\d{3,4}$/.test(v.cardCode.trim())) issue("cardCode", "Revisa el código.");
      if (!v.acceptConditions) issue("acceptConditions", "Acepta las condiciones para continuar.");
    });
}

/** Body of `POST /bookings` from valid values. */
/**
 * The body of `POST /bookings`. `isAccountHolder` says the signed-in user travels: the backend then
 * keeps their title, date of birth and gender for their next booking (nothing for someone else).
 */
export function buildBookingRequest(
  values: CheckoutValues,
  fare: Fare,
  isAccountHolder = false,
): BookingRequest {
  const bornOn = isoDateOf(values.birthDay, values.birthMonth, values.birthYear) ?? "";
  const passport = fare.requires_identity_documents
    ? [
        {
          type: "passport" as const,
          number: values.passportNumber.trim(),
          issuing_country_code: values.passportCountry,
          expires_on: isoDateOfText(values.passportExpiry) ?? "",
        },
      ]
    : [];
  return {
    offer_id: fare.offer_id,
    expected_price: fare.price.total,
    passenger: {
      title: values.title as PassengerTitle,
      traveller: {
        given_name: values.givenName.trim(),
        family_name: values.familyName.trim(),
        born_on: bornOn,
        gender: values.gender as "m" | "f",
        email: values.email.trim(),
        phone_number: toE164(values.phoneCountry, values.phoneNumber) ?? values.phoneNumber,
        identity_documents: passport,
      },
      is_account_holder: isAccountHolder,
    },
    payment_token: paymentToken(values.cardNumber),
  };
}

/** What to tell the traveler when a booking fails, and whether to send them back to "Tu viaje". */
export function failureMessage(code: FailureCode | null | undefined): {
  title: string;
  body: string;
  backToTrip: boolean;
} {
  switch (code) {
    case "offer_expired":
    case "offer_unavailable":
      return {
        title: "La tarifa ya no está disponible",
        body: "La aerolínea la dio de baja o venció. No se hizo ningún cobro. En Tu viaje puedes actualizar el precio y volver a intentar; los datos del pasajero quedan guardados.",
        backToTrip: true,
      };
    case "payment_declined":
      return {
        title: "La tarjeta fue rechazada",
        body: "No se hizo ningún cobro. Prueba con otra tarjeta.",
        backToTrip: false,
      };
    case "passenger_rejected":
      return {
        title: "La aerolínea no aceptó los datos del pasajero",
        body: "Revisa que coincidan con el documento de viaje y que el pasajero sea mayor de edad el día del vuelo. No se hizo ningún cobro.",
        backToTrip: false,
      };
    case "provider_rejected":
      return {
        title: "La aerolínea rechazó la reserva",
        body: "No se hizo ningún cobro. Revisa los datos y prueba de nuevo; si se repite, elige otra tarifa.",
        backToTrip: false,
      };
    default:
      return {
        title: "No pudimos confirmar con la aerolínea",
        body: "No se hizo ningún cobro. Prueba de nuevo en unos minutos.",
        backToTrip: false,
      };
  }
}

function conditionText(condition: FareCondition, action: "cambio" | "reembolso"): string {
  if (condition.allowed === false) return action === "cambio" ? "sin cambios" : "sin reembolso";
  if (condition.allowed !== true || !condition.penalty) return `${action}: sin dato`;
  if (isZero(condition.penalty)) return `${action} gratis`;
  return `${action} con cargo de ${formatPenalty(condition.penalty)}`;
}

/** "cambio con cargo de 200 GBP, sin reembolso" (design: conditions checkbox). */
export function conditionsSummary(fare: Fare): string {
  return `${conditionText(fare.conditions.change, "cambio")}, ${conditionText(fare.conditions.refund, "reembolso")}`;
}

/** "1 maleta + mano" (design: flight summary). `null` → "sin dato", never assumed. */
export function bagsSummary(fare: Fare): string {
  const checked = fareCheckedBags(fare);
  const carryOn = fareCarryOn(fare);
  const checkedText =
    checked === null
      ? "maleta: sin dato"
      : checked === 0
        ? "sin maleta"
        : `${checked} ${checked === 1 ? "maleta" : "maletas"}`;
  const carryOnText = carryOn === null ? "mano: sin dato" : carryOn === 0 ? "sin mano" : "mano";
  return `${checkedText} + ${carryOnText}`;
}

/**
 * The passenger fields filled from the signed-in account (design board "5 · con sesión"): given and
 * family name in capitals without accents, as the airline takes them, and the email. The rest of
 * the name goes to the family name («Pepe Perez» → PEPE / PEREZ).
 */
export function accountPassenger(account: {
  name: string;
  email: string;
}): Pick<CheckoutValues, "givenName" | "familyName" | "email"> {
  const [given = "", ...rest] = account.name.trim().split(/\s+/);
  const asAirline = (value: string) => toAirlineName(value) ?? value.toUpperCase();
  return { givenName: asAirline(given), familyName: asAirline(rest.join(" ")), email: account.email };
}

/**
 * The passenger data kept from the user's last booking for themselves («1990-08-23» → 23 / 08 / 1990).
 */
export function accountTraveller(profile: {
  title: PassengerTitle;
  born_on: string;
  gender: "m" | "f";
}): Pick<CheckoutValues, "title" | "gender" | "birthDay" | "birthMonth" | "birthYear"> {
  const [birthYear = "", birthMonth = "", birthDay = ""] = profile.born_on.split("-");
  return { title: profile.title, gender: profile.gender, birthDay, birthMonth, birthYear };
}

/**
 * The phone of the account split for the country selector and the number field
 * («+573105826464» → CO / «3105826464»), or `null` if it can't be read.
 */
export function accountPhone(e164: string): Pick<CheckoutValues, "phoneCountry" | "phoneNumber"> | null {
  const phone = parsePhoneNumberFromString(e164);
  if (!phone?.country) return null;
  return { phoneCountry: phone.country, phoneNumber: phone.nationalNumber };
}
