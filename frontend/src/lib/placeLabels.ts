import type { PlaceSuggestion } from "@/api/client";

/**
 * Names of the places the user picked, by IATA code.
 *
 * The URL only keeps codes (`to=NYC`); this remembers "New York · todos los aeropuertos" for the
 * session so the form and the titles show names, not just codes. Titles must use the searched
 * place: a search to NYC may land at JFK, EWR or SWF.
 */
const STORAGE_KEY = "booking-system.places";

interface RememberedPlace {
  /** Full description, for the form ("London · London Heathrow Airport"). */
  label: string;
  /** City, for titles ("London"). */
  city: string;
}

function read(): Record<string, RememberedPlace> {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function placeLabel(code: string | undefined): string | undefined {
  return code ? read()[code]?.label : undefined;
}

/** City of a picked place, e.g. "New York" for NYC; `undefined` if it wasn't picked this session. */
export function placeCity(code: string | undefined): string | undefined {
  return code ? read()[code]?.city : undefined;
}

/**
 * City to show for a searched code: the one the user picked, else the city of a result's airport
 * when it's that same code, else the code itself.
 */
export function searchedCity(code: string, resultPlace?: { code: string; city?: string | null }): string {
  return placeCity(code) ?? (resultPlace?.code === code ? resultPlace.city : undefined) ?? code;
}

export function rememberPlace(place: PlaceSuggestion): void {
  const entry: RememberedPlace = {
    label: describePlace(place),
    city: place.type === "city" ? place.name : (place.city ?? place.name),
  };
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...read(), [place.code]: entry }));
  } catch {
    // Storage unavailable (private mode): names are a convenience, codes still work.
  }
}

/** "New York · todos los aeropuertos" / "New York · John F Kennedy International Airport". */
export function describePlace(place: PlaceSuggestion): string {
  if (place.type === "city") return `${place.name} · todos los aeropuertos`;
  return place.city ? `${place.city} · ${place.name}` : place.name;
}
