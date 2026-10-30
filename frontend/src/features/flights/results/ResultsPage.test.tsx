import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useTrip } from "@/features/trip/public";
import { RESULTS_URL, renderApp } from "@/test/render";
import { FIXTURE_NOW, fixtures, server } from "@/test/server";

beforeEach(() => {
  // Only the clock is faked: the fixture's offers are valid until 21:26 UTC.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(FIXTURE_NOW);
});

const lufthansaCard = () => screen.getByRole("button", { name: /LX 317 · LX 14/ });

describe("results", () => {
  it("shows one card per flight, cheapest first", async () => {
    renderApp(RESULTS_URL);

    expect(await screen.findByText(/16 vuelos/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Ida: London a New York/ })).toBeInTheDocument();
    expect(screen.getByText("Más barato")).toBeInTheDocument();
    expect(screen.getByText(/Precios válidos por 26 min/)).toBeInTheDocument();
  });

  it("opens the fare matrix with «Sin dato» for an unreported cabin bag", async () => {
    const user = userEvent.setup();
    renderApp(RESULTS_URL);

    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));

    const matrix = screen.getByRole("table", { name: "Tarifas disponibles para este vuelo" });
    const columns = within(matrix)
      .getAllByRole("columnheader")
      .map((c) => c.textContent);
    expect(columns).toContain("Economy Impact");
    expect(within(matrix).getByText("Sin dato")).toBeInTheDocument();
    expect(within(matrix).getAllByText("No incluida").length).toBeGreaterThan(0);
    expect(within(matrix).getAllByText("300 GBP").length).toBeGreaterThan(0);
  });

  it("«Con maleta» hides fares without a checked bag", async () => {
    const user = userEvent.setup();
    renderApp(RESULTS_URL);
    await screen.findByText(/16 vuelos/);

    await user.click(screen.getByRole("button", { name: "Con maleta" }));
    await user.click(lufthansaCard());

    const matrix = screen.getByRole("table", { name: "Tarifas disponibles para este vuelo" });
    expect(within(matrix).queryByText("Economy Light")).not.toBeInTheDocument();
    expect(within(matrix).queryByText("No incluida")).not.toBeInTheDocument();
  });

  it("explains which filter to drop when none match", async () => {
    const user = userEvent.setup();
    renderApp(`${RESULTS_URL}&fDirect=true&fRefund=true&fTime=%22evening%22`);

    expect(await screen.findByText(/Ningún vuelo cumple los 3 filtros/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Quitar «Horario de salida»/ }));

    expect(await screen.findByText(/vuelo/)).toBeInTheDocument();
    expect(screen.queryByText(/Ningún vuelo cumple/)).not.toBeInTheDocument();
  });

  it("offers to refresh prices once the search expires", async () => {
    renderApp(RESULTS_URL);
    await screen.findByText(/16 vuelos/);

    vi.setSystemTime(new Date("2026-10-23T21:30:00Z"));

    expect(
      await screen.findByText(/Los precios de esta búsqueda vencieron/, {}, { timeout: 2000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actualizar precios" })).toBeInTheDocument();
  });

  it("shows a friendly error when the provider times out", async () => {
    server.use(
      http.post("*/api/v1/flights/search", () =>
        HttpResponse.json({ error: { code: "provider_timeout", message: "timeout" } }, { status: 504 }),
      ),
    );
    renderApp(RESULTS_URL);

    expect(await screen.findByText("No pudimos completar la búsqueda")).toBeInTheDocument();
    expect(screen.getByText(/no respondieron a tiempo/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

describe("adding to the trip", () => {
  it("choosing a fare saves it and opens «Tu viaje»", async () => {
    const user = userEvent.setup();
    renderApp(RESULTS_URL);
    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));

    await user.click(screen.getByRole("button", { name: /Elegir Economy Light/ }));

    expect(await screen.findByRole("heading", { name: "Tu viaje a New York" })).toBeInTheDocument();
    expect(screen.getByText("Agregaste el vuelo a tu viaje.")).toBeInTheDocument();
    expect(screen.getByText(/Precio válido 26 min/)).toBeInTheDocument();
    expect(useTrip.getState().order).toHaveLength(1);
  });

  it("going back and choosing the same fare doesn't duplicate it", async () => {
    const user = userEvent.setup();
    const { router } = renderApp(RESULTS_URL);
    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));
    await user.click(screen.getByRole("button", { name: /Elegir Economy Light/ }));
    await screen.findByRole("heading", { name: "Tu viaje a New York" });

    router.history.back();
    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));
    await user.click(screen.getByRole("button", { name: /Elegir Economy Light/ }));

    expect(await screen.findByText("Este vuelo ya está en tu viaje.")).toBeInTheDocument();
    expect(useTrip.getState().order).toHaveLength(1);
  });

  it("another fare of the same flight replaces it, with undo", async () => {
    const user = userEvent.setup();
    const { router } = renderApp(RESULTS_URL);
    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));
    await user.click(screen.getByRole("button", { name: /Elegir Economy Light/ }));
    await screen.findByRole("heading", { name: "Tu viaje a New York" });

    router.history.back();
    await user.click(await screen.findByRole("button", { name: /LX 317 · LX 14/ }));
    await user.click(screen.getByRole("button", { name: /Elegir Economy Flex/ }));

    expect(await screen.findByText("Cambiaste la tarifa a Economy Flex.")).toBeInTheDocument();
    expect(useTrip.getState().order).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Deshacer" }));
    await waitFor(() => {
      const [item] = Object.values(useTrip.getState().items);
      expect(item?.fare.slices[0]?.fare_brand).toBe("Economy Light");
    });
  });
});

describe("round trip in two steps", () => {
  const ROUND_TRIP_URL = `${RESULTS_URL}&ret=2026-12-22`;

  beforeEach(() => {
    server.use(http.post("*/api/v1/flights/search", () => HttpResponse.json(fixtures.roundTrip)));
  });

  it("lists each outbound once, then only the returns of the chosen one", async () => {
    const user = userEvent.setup();
    renderApp(ROUND_TRIP_URL);

    expect(await screen.findByRole("heading", { name: /Elige tu ida/ })).toBeInTheDocument();
    expect(screen.getByText(/7 idas/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /LX 339 · LX 14/ }));

    expect(await screen.findByRole("heading", { name: /Elige tu vuelta/ })).toBeInTheDocument();
    expect(screen.getByText(/17 vueltas para esta ida/)).toBeInTheDocument();
    expect(screen.getByText("Ida elegida")).toBeInTheDocument();
  });

  it("a return opens the fares of the whole round trip", async () => {
    const user = userEvent.setup();
    renderApp(ROUND_TRIP_URL);
    await user.click(await screen.findByRole("button", { name: /LX 339 · LX 14/ }));

    const [firstReturn] = await screen.findAllByRole("button", { name: /Ida y vuelta desde/ });
    await user.click(firstReturn as HTMLElement);

    expect(screen.getByRole("table", { name: "Tarifas disponibles para este vuelo" })).toBeInTheDocument();
  });

  it("the returns follow the chosen order", async () => {
    const user = userEvent.setup();
    renderApp(`${ROUND_TRIP_URL}&sort=departure`);
    await user.click(await screen.findByRole("button", { name: /LX 339 · LX 14/ }));
    await screen.findByRole("heading", { name: /Elige tu vuelta/ });

    const departures = screen
      .getAllByRole("article")
      .map((card) => card.textContent?.match(/Vuelta(\d{2}:\d{2})/)?.[1] ?? "");
    expect(departures.length).toBeGreaterThan(1);
    expect(departures).toEqual([...departures].sort());
  });

  it("«Cambiar ida» goes back to the outbounds", async () => {
    const user = userEvent.setup();
    renderApp(ROUND_TRIP_URL);
    await user.click(await screen.findByRole("button", { name: /LX 339 · LX 14/ }));

    await user.click(await screen.findByRole("button", { name: "Cambiar ida" }));

    expect(await screen.findByText(/7 idas/)).toBeInTheDocument();
  });
});
