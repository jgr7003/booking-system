import { describe, expect, it } from "vitest";
import type { Fare, Flight } from "@/api/client";
import { fareName } from "@/lib/flights/fares";
import type { CompleteSearch } from "@/lib/flights/search";
import { fixtures } from "@/test/server";
import { itemKeyOf, makeTripItem, type TripItems, tripItems, upsertItem, useTrip } from "./store";

const search: CompleteSearch = { from: "LHR", to: "JFK", depart: "2026-12-15" };
const [cheapest, second] = fixtures.search.flights as [Flight, Flight];
const lufthansa = fixtures.search.flights.find((f) => f.fares.length === 5) as Flight;
const light = lufthansa.fares.find((f) => fareName(f) === "Economy Light") as Fare;
const flex = lufthansa.fares.find((f) => fareName(f) === "Economy Flex") as Fare;
const empty: TripItems = { items: {}, order: [] };

describe("trip idempotency", () => {
  it("item key is provider + itinerary key", () => {
    expect(itemKeyOf(lufthansa)).toBe(`duffel:${lufthansa.key}`);
  });

  it("the same offer twice (back button, double click) is one item", () => {
    const first = upsertItem(empty, makeTripItem(lufthansa, light, search, "orq_1"));
    const again = upsertItem(first.next, makeTripItem(lufthansa, light, search, "orq_1"));

    expect(again.result.status).toBe("unchanged");
    expect(again.next).toBe(first.next);
    expect(tripItems(again.next)).toHaveLength(1);
  });

  it("another fare of the same flight replaces it", () => {
    const first = upsertItem(empty, makeTripItem(lufthansa, light, search, "orq_1"));
    const changed = upsertItem(first.next, makeTripItem(lufthansa, flex, search, "orq_1"));

    expect(changed.result.status).toBe("replaced");
    expect(tripItems(changed.next).map((i) => fareName(i.fare))).toEqual(["Economy Flex"]);
  });

  it("the same flight from a new search (new offer id) replaces the expired offer", () => {
    const first = upsertItem(empty, makeTripItem(lufthansa, light, search, "orq_1"));
    const renewed = { ...light, offer_id: "off_renewed" };
    const refreshed = upsertItem(first.next, makeTripItem(lufthansa, renewed, search, "orq_2"));

    expect(refreshed.result.status).toBe("replaced");
    expect(tripItems(refreshed.next)[0]?.fare.offer_id).toBe("off_renewed");
  });

  it("other flights are added in order, and a replaced one keeps its place", () => {
    let state = empty;
    for (const flight of [cheapest, second, lufthansa]) {
      state = upsertItem(state, makeTripItem(flight, flight.fares[0] as Fare, search, "orq_1")).next;
    }
    state = upsertItem(
      state,
      makeTripItem(cheapest, { ...(cheapest.fares[0] as Fare), offer_id: "off_x" }, search, "orq_2"),
    ).next;

    expect(tripItems(state).map((i) => i.itemKey)).toEqual([cheapest, second, lufthansa].map(itemKeyOf));
  });

  it("stored items don't carry the other fares of the flight", () => {
    const item = makeTripItem(lufthansa, light, search, "orq_1");
    expect("fares" in item.flight).toBe(false);
  });

  it("remove and restore (undo) keep the position", () => {
    const store = useTrip.getState();
    for (const flight of [cheapest, second, lufthansa])
      store.add(makeTripItem(flight, flight.fares[0] as Fare, search, "orq_1"));

    const removed = useTrip.getState().remove(itemKeyOf(second));
    expect(useTrip.getState().order).toHaveLength(2);
    useTrip.getState().restore(removed?.item as never, removed?.index);

    expect(useTrip.getState().order).toEqual([cheapest, second, lufthansa].map(itemKeyOf));
  });
});
