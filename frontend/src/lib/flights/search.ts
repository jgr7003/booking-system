/**
 * Flight search criteria: their URL params (TanStack Router + Zod), validation and the API request.
 * Shared by the search, the results, "Tu viaje" and the confirmation, which link back to a search.
 */
import { z } from "zod";
import type { CabinClass, SearchCriteria } from "@/api/client";

export const CABINS = [
  "economy",
  "premium_economy",
  "business",
  "first",
] as const satisfies readonly CabinClass[];

export const CABIN_LABELS: Record<CabinClass, string> = {
  economy: "Económica",
  premium_economy: "Premium economy",
  business: "Business",
  first: "Primera",
};

/** Same limits the backend validates (app/flights/domain/constants.py). */
export const MAX_PASSENGERS = 9;

/** Passengers per booking in the current version: one adult (00-global.md, decision 31). */
export const BOOKABLE_PASSENGERS = 1;
export const INFANT_MAX_AGE = 1;
export const MAX_CHILD_AGE = 17;

// Each field falls back to `undefined` instead of failing: a broken URL shows the search form.
const iata = z
  .string()
  .regex(/^[A-Z0-9]{3}$/)
  .optional()
  .catch(undefined);
const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .optional()
  .catch(undefined);

/** Search criteria as URL search params (`/flights?from=LHR&to=JFK&depart=2026-12-15`). */
export const flightSearchSchema = z.object({
  from: iata,
  to: iata,
  depart: isoDate,
  ret: isoDate,
  adults: z.number().int().min(1).max(MAX_PASSENGERS).optional().catch(undefined),
  children: z.array(z.number().int().min(0).max(MAX_CHILD_AGE)).optional().catch(undefined),
  cabin: z.enum(CABINS).optional().catch(undefined),
  direct: z.boolean().optional().catch(undefined),
});

export const SORTS = ["price", "duration", "departure"] as const;
export const TIME_WINDOWS = ["morning", "afternoon", "evening"] as const;

/** Results page: criteria plus the view state (sort, filters, highlighted flight). */
export const resultsSearchSchema = flightSearchSchema.extend({
  sort: z.enum(SORTS).optional().catch(undefined),
  fDirect: z.boolean().optional().catch(undefined),
  fBag: z.boolean().optional().catch(undefined),
  fRefund: z.boolean().optional().catch(undefined),
  fTime: z.enum(TIME_WINDOWS).optional().catch(undefined),
  fAirlines: z.array(z.string()).optional().catch(undefined),
  hl: z.string().optional().catch(undefined),
  /** Chosen outbound when a round trip is shown in two steps (see `groupByOutbound`). */
  out: z.string().optional().catch(undefined),
});

/** Detail page: criteria plus the selected fare. */
export const detailSearchSchema = flightSearchSchema.extend({
  fare: z.string().optional().catch(undefined),
  /** "trip" when the detail was opened from "Tu viaje" (changes the back link and the current step). */
  via: z.enum(["trip"]).optional().catch(undefined),
});

export type FlightSearch = z.infer<typeof flightSearchSchema>;
export type ResultsSearch = z.infer<typeof resultsSearchSchema>;
export type DetailSearch = z.infer<typeof detailSearchSchema>;

/** A search with every required field present. */
export type CompleteSearch = FlightSearch & { from: string; to: string; depart: string };

export function isComplete(search: FlightSearch): search is CompleteSearch {
  return Boolean(search.from && search.to && search.depart);
}

/** Only the criteria fields, e.g. to build links that keep the search but drop the view state. */
export function pickSearch(search: FlightSearch): FlightSearch {
  const { from, to, depart, ret, adults, children, cabin, direct } = search;
  return { from, to, depart, ret, adults, children, cabin, direct };
}

/** URL search → body of `POST /api/v1/flights/search`. */
export function toCriteria(search: CompleteSearch): SearchCriteria {
  return {
    origin: search.from,
    destination: search.to,
    departure_date: search.depart,
    return_date: search.ret ?? null,
    passengers: { adults: search.adults ?? 1, children_ages: search.children ?? [] },
    cabin_class: search.cabin ?? null,
    max_connections: search.direct ? 0 : 1,
  };
}

/** Problems with the passengers, or `null` if they're valid. */
export function passengersError(adults: number, childrenAges: number[]): string | null {
  if (adults < 1) return "Tiene que viajar al menos un adulto.";
  if (adults + childrenAges.length > MAX_PASSENGERS)
    return `Como máximo ${MAX_PASSENGERS} pasajeros por reserva.`;
  const infants = childrenAges.filter((age) => age <= INFANT_MAX_AGE).length;
  if (infants > adults) return "Cada menor de 0 o 1 año viaja en brazos de un adulto distinto.";
  return null;
}

/** Problems with the search form, by field. Empty when it can be submitted. */
export function searchErrors(
  search: FlightSearch,
  today: string,
): Partial<Record<keyof FlightSearch, string>> {
  const errors: Partial<Record<keyof FlightSearch, string>> = {};
  if (!search.from) errors.from = "Elige el origen.";
  if (!search.to) errors.to = "Elige el destino.";
  if (search.from && search.from === search.to) errors.to = "El destino tiene que ser distinto del origen.";
  if (!search.depart) errors.depart = "Elige la fecha de ida.";
  else if (search.depart < today) errors.depart = "La ida no puede ser en el pasado.";
  if (search.ret && search.depart && search.ret < search.depart)
    errors.ret = "La vuelta no puede ser antes de la ida.";
  const passengers = passengersError(search.adults ?? 1, search.children ?? []);
  if (passengers) errors.adults = passengers;
  return errors;
}
