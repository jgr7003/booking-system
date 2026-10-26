import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import type { PlaceSuggestion, SearchResponse } from "@/api/client";
import places from "./fixtures/places-new-y.json";
import search from "./fixtures/search-lhr-jfk.json";
import roundTrip from "./fixtures/search-lhr-jfk-roundtrip.json";

/**
 * Real API responses: the search fixture is the captured Duffel answer (LHR → JFK, 56 offers)
 * processed by the backend's own service and public schemas (also a round trip: 7 outbounds,
 * 55 combinations); the places one comes from the API.
 */
export const fixtures = {
  search: search as SearchResponse,
  roundTrip: roundTrip as SearchResponse,
  places: places as PlaceSuggestion[],
};

/** Expiry of the fixture's offers: tests set the clock before it so offers are valid. */
export const FIXTURE_NOW = new Date("2026-10-23T21:00:00Z");

export const handlers = [
  http.post("*/api/v1/flights/search", () => HttpResponse.json(fixtures.search)),
  http.get("*/api/v1/flights/places", () => HttpResponse.json(fixtures.places)),
];

/** Every request must be mocked: an unexpected one fails the test (same rule as the backend). */
export const server = setupServer(...handlers);
