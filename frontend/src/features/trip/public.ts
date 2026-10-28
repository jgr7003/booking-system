/**
 * What "Tu viaje" offers the other features: the trip itself and saving a fare in it.
 * Other features import only this file (enforced by Biome, see `biome.json`).
 */
export { makeTripItem, type TripItem, tripItems, useTrip } from "./store";
export { useAddToTrip } from "./useAddToTrip";
