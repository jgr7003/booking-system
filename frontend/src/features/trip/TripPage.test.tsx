import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "@/test/render";
import { fixtures, server } from "@/test/server";
import { makeTripItem, useTrip } from "./store";

function addToTrip(flight: (typeof fixtures.search.flights)[number] | undefined) {
  const fare = flight?.fares[0];
  if (!flight || !fare) throw new Error("fixture without flights");
  useTrip
    .getState()
    .add(makeTripItem(flight, fare, { from: "LHR", to: "JFK", depart: "2026-12-15" }, "orq_1"));
}

describe("trip summary", () => {
  it("marks a two-way flight as «Ida y vuelta»", async () => {
    const roundTrip = fixtures.roundTrip.flights.find((f) => f.slices.length > 1);
    addToTrip(roundTrip);
    renderApp("/trip");

    const summary = await screen.findByRole("complementary", { name: "Resumen del viaje" });
    expect(within(summary).getByText("Ida y vuelta")).toBeInTheDocument();
  });

  it("refreshes an expired price with a new search", async () => {
    // The fixture's offers expired long before today, so the card offers to refresh them.
    addToTrip(fixtures.search.flights[0]);
    renderApp("/trip");

    await userEvent.click(await screen.findByRole("button", { name: "Actualizar precio" }));

    expect(await screen.findByText(/^Precio actualizado: /)).toBeInTheDocument();
  });

  it("says so when the price can't be refreshed", async () => {
    server.use(http.post("*/api/v1/flights/search", () => HttpResponse.json({}, { status: 503 })));
    addToTrip(fixtures.search.flights[0]);
    renderApp("/trip");

    await userEvent.click(await screen.findByRole("button", { name: "Actualizar precio" }));

    expect(
      await screen.findByText("No pudimos actualizar el precio. Prueba de nuevo en unos segundos."),
    ).toBeInTheDocument();
  });

  it("doesn't mark a one-way flight", async () => {
    addToTrip(fixtures.search.flights[0]);
    renderApp("/trip");

    const summary = await screen.findByRole("complementary", { name: "Resumen del viaje" });
    expect(within(summary).queryByText("Ida y vuelta")).not.toBeInTheDocument();
  });
});
