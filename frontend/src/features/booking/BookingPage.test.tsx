import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http, type JsonBodyType } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Booking } from "@/api/client";
import { makeTripItem, useTrip } from "@/features/trip/public";
import { installFakeEventSource } from "@/test/eventSource";
import { renderApp } from "@/test/render";
import { fixtures, server } from "@/test/server";
import { signInForTests } from "@/test/session";

const { confirmedRoundTrip: roundTrip, failedDeclined, processing } = fixtures.bookings;

beforeEach(async () => {
  installFakeEventSource();
  await signInForTests();
});

function serve(booking: JsonBodyType, status = 200) {
  server.use(http.get("*/api/v1/flights/bookings/:id", () => HttpResponse.json(booking, { status })));
}

describe("confirmation", () => {
  it("summarizes the whole trip: route, both dates, passenger and booking reference", async () => {
    serve(roundTrip);
    renderApp(`/bookings/${roundTrip.id}`);

    expect(await screen.findByRole("heading", { name: "Reserva confirmada y pagada" })).toBeInTheDocument();
    expect(screen.getByText("Ida y vuelta · 1 pasajero")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "ida y vuelta" })).toBeInTheDocument();
    expect(screen.getAllByText("mar 10 nov 2026").length).toBeGreaterThan(0);
    expect(screen.getAllByText("dom 15 nov 2026").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sr. PEPE PEREZ").length).toBeGreaterThan(0);
    expect(screen.getByText("GNA3VA")).toBeInTheDocument();
    expect(screen.getByText("Lo pide British Airways para el check-in")).toBeInTheDocument();
  });

  it("shows each slice with its label, date and operating airline", async () => {
    serve(roundTrip);
    renderApp(`/bookings/${roundTrip.id}`);

    const outbound = await screen.findByRole("article", { name: "Vuelo de ida" });
    const inbound = screen.getByRole("article", { name: "Vuelo de vuelta" });
    expect(within(outbound).getByText("IDA")).toBeInTheDocument();
    expect(within(inbound).getByText("dom 15 nov 2026")).toBeInTheDocument();
    expect(within(inbound).getByText("10:50")).toBeInTheDocument();
    expect(within(outbound).getAllByText("British Airways").length).toBeGreaterThan(0);
  });

  it("shows what the fare includes once, since both slices match", async () => {
    serve(roundTrip);
    renderApp(`/bookings/${roundTrip.id}`);

    const included = await screen.findByRole("region", { name: "Qué incluye tu tarifa Basic" });
    expect(within(included).getByText("Igual en la ida y en la vuelta")).toBeInTheDocument();
    expect(within(included).getAllByText("✗ No permite")).toHaveLength(2);
    expect(within(included).getAllByText("Sin dato")).toHaveLength(2);
  });

  it("explains what can be managed, without fake buttons", async () => {
    serve(roundTrip);
    renderApp(`/bookings/${roundTrip.id}`);

    const manage = await screen.findByRole("region", { name: "Gestionar reserva" });
    expect(within(manage).queryAllByRole("button")).toEqual([]);
    expect(within(manage).getByText("Tu tarifa Basic no permite cambios.")).toBeInTheDocument();
    expect(within(manage).getByText("Tu tarifa Basic no tiene reembolso.")).toBeInTheDocument();
  });

  it("copies the booking reference", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(navigator, "clipboard", "get").mockReturnValue({ writeText } as unknown as Clipboard);
    serve(roundTrip);
    renderApp(`/bookings/${roundTrip.id}`);

    await user.click(await screen.findByRole("button", { name: "Copiar" }));

    expect(writeText).toHaveBeenCalledWith("GNA3VA");
    expect(await screen.findByRole("button", { name: "✓ Copiado" })).toBeInTheDocument();
  });

  it("uses airport codes and names when the cities are missing", async () => {
    const missing = structuredClone(roundTrip) as Booking;
    for (const slice of missing.order?.slices ?? []) {
      slice.origin.city = null;
      slice.destination.city = null;
    }
    serve(missing);
    renderApp(`/bookings/${roundTrip.id}`);

    expect(
      await screen.findByText(
        "El Dorado International Airport ⇄ Alfonso Bonilla Aragón International Airport",
      ),
    ).toBeInTheDocument();
  });

  it("says it's confirming while the airline answers, and updates on its own", async () => {
    serve(processing);
    renderApp(`/bookings/${processing.id}`);

    expect(await screen.findByText("Estamos confirmando tu reserva con la aerolínea")).toBeInTheDocument();
    expect(screen.getByText("Confirmando el lugar con la aerolínea")).toHaveAttribute("aria-current", "step");
    expect(await screen.findByText(/Se cobra recién cuando la aerolínea confirma/)).toBeInTheDocument();
  });

  it("tells the traveler it is taking longer than usual after a minute, and that an email will follow", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(new Date(processing.created_at).getTime() + 61_000));
    serve(processing);
    renderApp(`/bookings/${processing.id}`);

    expect(await screen.findByText("Está tardando más de lo habitual")).toBeInTheDocument();
    expect(screen.getByText(/te la enviamos por correo/)).toBeInTheDocument();
  });

  it("doesn't say it before the minute", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(new Date(processing.created_at).getTime() + 30_000));
    serve(processing);
    renderApp(`/bookings/${processing.id}`);

    expect(await screen.findByText(/Se cobra recién cuando la aerolínea confirma/)).toBeInTheDocument();
    expect(screen.queryByText("Está tardando más de lo habitual")).not.toBeInTheDocument();
  });

  it("explains a failed booking, that nothing was charged, and what was attempted", async () => {
    const flight = fixtures.search.flights[0];
    const fare = flight?.fares[0];
    if (!flight || !fare) throw new Error("fixture without flights");
    const item = makeTripItem(flight, fare, { from: "LHR", to: "JFK", depart: "2026-12-15" }, "orq_1");
    useTrip.getState().add(item);
    serve(failedDeclined);
    renderApp(`/bookings/${failedDeclined.id}`);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("La tarjeta fue rechazada.")).toBeInTheDocument();
    expect(within(alert).getByText(/No se cobró nada/)).toBeInTheDocument();
    expect(within(alert).getByText(/Intentaste reservar/)).toBeInTheDocument();
    await waitFor(() =>
      expect(within(alert).getByRole("link", { name: "Probar con otra tarjeta" })).toHaveAttribute(
        "href",
        `/checkout/${encodeURIComponent(item.itemKey)}`,
      ),
    );
  });

  it("shows an issuance error without a booking reference and without offering to book again", async () => {
    const issuanceError = {
      ...processing,
      status: "issuance_error",
      failure_code: "capture_failed",
      version: 4,
    } as Booking;
    serve(issuanceError);
    renderApp(`/bookings/${issuanceError.id}`);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("Error de emisión")).toBeInTheDocument();
    expect(within(alert).getByText(/No vuelvas a reservar este vuelo/)).toBeInTheDocument();
    expect(within(alert).getByText(issuanceError.id)).toBeInTheDocument();
    expect(screen.queryByText("Reserva confirmada y pagada")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Volver a Tu viaje|Probar con otra tarjeta/ }),
    ).not.toBeInTheDocument();
  });

  it("says so when the booking doesn't exist", async () => {
    serve({ error: { code: "booking_not_found", message: "Booking not found." } }, 404);
    renderApp("/bookings/00000000-0000-0000-0000-000000000000");

    expect(await screen.findByText("No encontramos esta reserva")).toBeInTheDocument();
  });
});
