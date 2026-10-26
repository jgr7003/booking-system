import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api, type PlaceSuggestion, type SearchCriteria, type SearchResponse, unwrap } from "./client";

export const flightKeys = {
  search: (criteria: SearchCriteria) => ["flights", "search", criteria] as const,
  places: (query: string) => ["flights", "places", query] as const,
};

export async function searchFlights(criteria: SearchCriteria, signal?: AbortSignal): Promise<SearchResponse> {
  return unwrap(await api.POST("/api/v1/flights/search", { body: criteria, signal }));
}

export async function suggestPlaces(query: string, signal?: AbortSignal): Promise<PlaceSuggestion[]> {
  return unwrap(await api.GET("/api/v1/flights/places", { params: { query: { q: query } }, signal }));
}

/**
 * Searches flights for `criteria` (no request while it's `null`).
 *
 * Results are kept while the user moves between results, detail and trip; they're not
 * refetched on their own because each search creates offers that expire. Retrying is explicit.
 */
export function useFlightSearch(criteria: SearchCriteria | null) {
  return useQuery({
    queryKey: criteria ? flightKeys.search(criteria) : ["flights", "search", "idle"],
    // No abort signal on purpose: React Query only cancels queries whose fn uses the signal, and
    // StrictMode mounts twice in development, so it aborted the first request and sent another.
    // Each search creates an offer request at the provider; a duplicate is real cost.
    queryFn: () => searchFlights(criteria as SearchCriteria),
    enabled: criteria !== null,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 30 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
  });
}

/** Airport and city suggestions; the caller debounces `query`. */
export function usePlaceSuggestions(query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: flightKeys.places(trimmed.toLowerCase()),
    // Without the signal the request isn't aborted on remount (see useFlightSearch).
    queryFn: () => suggestPlaces(trimmed),
    enabled: trimmed.length >= 2,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}
