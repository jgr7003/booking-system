import createClient from "openapi-fetch";
import type { components, paths } from "./schema";
import { authMiddleware } from "./session";

/** Schemas of the backend API, generated from its OpenAPI (`pnpm gen:api`). */
export type Schemas = components["schemas"];
export type SearchCriteria = Schemas["SearchCriteria"];
export type SearchResponse = Schemas["SearchResponse"];
export type Flight = Schemas["FlightResponse"];
export type Fare = Schemas["FareResponse"];
export type FlightSlice = Schemas["FlightSlice"];
export type FlightSegment = Schemas["FlightSegment"];
export type FareCondition = Schemas["FareCondition"];
// Money is in requests and responses, so the OpenAPI has two variants; responses carry the amount as text.
export type Money = Schemas["Money-Output"];
export type PlaceSuggestion = Schemas["PlaceSuggestion"];
export type CabinClass = NonNullable<SearchCriteria["cabin_class"]>;
export type Booking = Schemas["BookingResponse"];
export type BookingRequest = Schemas["BookingRequest"];
export type BookingStatus = Booking["status"];
export type FailureCode = NonNullable<Booking["failure_code"]>;
export type PassengerTitle = Schemas["PassengerTitle"];
export type PriceDecisionRequest = Schemas["PriceDecisionRequest"];
export type OrderSlice = Schemas["Slice"];
export type OrderSegment = Schemas["Segment"];

/** Error of the platform's API: `{"error": {"code", "message"}}`. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = createClient<paths>({
  // Absolute base URL: Node's fetch (tests) doesn't resolve relative URLs.
  baseUrl: typeof window === "undefined" ? "" : window.location.origin,
  // Look fetch up on every request instead of keeping the one present at import time, so
  // interceptors installed later (MSW in tests) see the requests.
  fetch: (request) => globalThis.fetch(request),
});

// Every request is signed by the device key and carries the session, if any (src/api/session.ts).
api.use(authMiddleware);

/**
 * Unwraps an openapi-fetch result, turning API errors into `ApiError`.
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data;
  const body = result.error as { error?: { code?: string; message?: string } } | undefined;
  throw new ApiError(
    result.response.status,
    body?.error?.code ?? "unknown_error",
    body?.error?.message ?? "Unexpected error",
  );
}
