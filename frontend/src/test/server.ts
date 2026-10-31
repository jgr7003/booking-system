import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import type { Booking, PlaceSuggestion, SearchResponse } from "@/api/client";
import awaitingPrice from "@/test/fixtures/booking-awaiting-price.json";
import cancelled from "@/test/fixtures/booking-cancelled.json";
import confirmed from "@/test/fixtures/booking-confirmed.json";
import confirmedRoundTrip from "@/test/fixtures/booking-confirmed-roundtrip.json";
import failedDeclined from "@/test/fixtures/booking-failed-declined.json";
import pending from "@/test/fixtures/booking-pending.json";
import processing from "@/test/fixtures/booking-processing.json";
import places from "@/test/fixtures/places-new-y.json";
import search from "@/test/fixtures/search-lhr-jfk.json";
import roundTrip from "@/test/fixtures/search-lhr-jfk-roundtrip.json";
import { TEST_ME } from "@/test/session";

/**
 * Real API responses: the search fixture is the captured Duffel answer (LHR → JFK, 56 offers)
 * processed by the backend's own service and public schemas (also a round trip: 7 outbounds,
 * 55 combinations); the places one comes from the API. The bookings are the backend's public
 * schema of each state, for the first fare of the search (the confirmed one with the captured
 * Duffel order).
 */
export const fixtures = {
  search: search as SearchResponse,
  roundTrip: roundTrip as SearchResponse,
  places: places as PlaceSuggestion[],
  bookings: {
    pending: pending as Booking,
    processing: processing as Booking,
    awaitingPrice: awaitingPrice as Booking,
    confirmed: confirmed as Booking,
    /** A real round trip Bogotá ⇄ Cali confirmed in Duffel test (as `GET /bookings/{id}` returns it). */
    confirmedRoundTrip: confirmedRoundTrip as Booking,
    failedDeclined: failedDeclined as Booking,
    cancelled: cancelled as Booking,
  },
};

/** Expiry of the fixture's offers: tests set the clock before it so offers are valid. */
export const FIXTURE_NOW = new Date("2026-10-23T21:00:00Z");

/** Sign-in methods of the main installation: Google and email, as the backend answers them. */
export const platformMethods = {
  organization_name: null,
  password_enabled: true,
  signup_enabled: true,
  providers: [{ slug: "google", display_name: "Google" }],
};

export const handlers = [
  http.get("*/api/v1/auth/methods", () => HttpResponse.json(platformMethods)),
  http.get("*/api/v1/me", () => HttpResponse.json(TEST_ME)),
  http.post("*/api/v1/flights/search", () => HttpResponse.json(fixtures.search)),
  http.get("*/api/v1/flights/places", () => HttpResponse.json(fixtures.places)),
];

/** Every request must be mocked: an unexpected one fails the test (same rule as the backend). */
export const server = setupServer(...handlers);
