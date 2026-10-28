import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { Fare, Flight } from "@/api/client";
import type { CompleteSearch } from "@/lib/flights/search";

/**
 * A flight saved in "Tu viaje" with the chosen fare.
 *
 * `itemKey` identifies the flight (not the offer): the same flight chosen again, with another
 * fare or from a new search, replaces the item instead of duplicating it.
 */
export interface TripItem {
  itemKey: string;
  flight: Omit<Flight, "fares">;
  fare: Fare;
  search: CompleteSearch;
  searchId: string;
  addedAt: number;
}

export type AddResult =
  | { status: "added"; item: TripItem }
  | { status: "unchanged"; item: TripItem }
  | { status: "replaced"; item: TripItem; previous: TripItem };

/** Idempotency key of a trip item: provider + itinerary key. */
export function itemKeyOf(flight: Pick<Flight, "provider" | "key">): string {
  return `${flight.provider}:${flight.key}`;
}

export function makeTripItem(
  flight: Flight,
  fare: Fare,
  search: CompleteSearch,
  searchId: string,
  now = Date.now(),
): TripItem {
  const { fares: _fares, ...rest } = flight;
  return { itemKey: itemKeyOf(flight), flight: rest, fare, search, searchId, addedAt: now };
}

export interface TripItems {
  items: Record<string, TripItem>;
  order: string[];
}

/**
 * Adds an item idempotently (pure, for tests and the store).
 *
 * - Same offer already there → unchanged.
 * - Same flight with another fare or a renewed offer → replaced, keeping its position.
 * - Another flight → added at the end.
 */
export function upsertItem(state: TripItems, item: TripItem): { next: TripItems; result: AddResult } {
  const existing = state.items[item.itemKey];
  if (existing?.fare.offer_id === item.fare.offer_id) {
    return { next: state, result: { status: "unchanged", item: existing } };
  }
  const next: TripItems = {
    items: { ...state.items, [item.itemKey]: item },
    order: existing ? state.order : [...state.order, item.itemKey],
  };
  return {
    next,
    result: existing ? { status: "replaced", item, previous: existing } : { status: "added", item },
  };
}

interface TripState extends TripItems {
  add: (item: TripItem) => AddResult;
  remove: (itemKey: string) => { item: TripItem; index: number } | undefined;
  restore: (item: TripItem, index?: number) => void;
  clear: () => void;
}

export const useTrip = create<TripState>()(
  persist(
    (set, get) => ({
      items: {},
      order: [],
      add: (item) => {
        const { next, result } = upsertItem(get(), item);
        if (result.status !== "unchanged") set(next);
        return result;
      },
      remove: (itemKey) => {
        const { items, order } = get();
        const item = items[itemKey];
        if (!item) return undefined;
        const { [itemKey]: _removed, ...rest } = items;
        set({ items: rest, order: order.filter((k) => k !== itemKey) });
        return { item, index: order.indexOf(itemKey) };
      },
      restore: (item, index) => {
        const { items, order } = get();
        const without = order.filter((k) => k !== item.itemKey);
        const at = index === undefined ? without.length : Math.min(index, without.length);
        set({
          items: { ...items, [item.itemKey]: item },
          order: [...without.slice(0, at), item.itemKey, ...without.slice(at)],
        });
      },
      clear: () => set({ items: {}, order: [] }),
    }),
    {
      name: "booking-system.trip",
      version: 1,
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ items, order }) => ({ items, order }),
    },
  ),
);

export function tripItems(state: TripItems): TripItem[] {
  return state.order.map((k) => state.items[k]).filter((i): i is TripItem => i !== undefined);
}
