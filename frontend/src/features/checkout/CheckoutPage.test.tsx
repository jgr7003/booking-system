import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Booking, BookingRequest } from "@/api/client";
import { makeTripItem, useTrip } from "@/features/trip/public";
import { clearSession } from "@/lib/auth/tokens";
import { FakeEventSource, installFakeEventSource } from "@/test/eventSource";
import { renderApp } from "@/test/render";
import { FIXTURE_NOW, fixtures, server } from "@/test/server";
import { signInForTests, TEST_ME, TEST_USER } from "@/test/session";
import { EMPTY_VALUES } from "./logic";
import { useCheckout } from "./store";

const BOOKINGS = "*/api/v1/flights/bookings";
const { bookings } = fixtures;

function addFlightToTrip() {
  const flight = fixtures.search.flights[0];
  const fare = flight?.fares[0];
  if (!flight || !fare) throw new Error("fixture without flights");
  const item = makeTripItem(
    flight,
    fare,
    { from: "LHR", to: "JFK", depart: "2026-12-15" },
    fixtures.search.search_id,
  );
  useTrip.getState().add(item);
  return item;
}

/** Records the bookings requests and answers each with the next booking state. */
function bookingApi(created: Booking, states: Booking[] = []) {
  const posts: { body: BookingRequest; key: string | null }[] = [];
  let current = created;
  server.use(
    http.post(BOOKINGS, async ({ request }) => {
      posts.push({
        body: (await request.json()) as BookingRequest,
        key: request.headers.get("Idempotency-Key"),
      });
      return HttpResponse.json(created, { status: 202 });
    }),
    http.get(`${BOOKINGS}/:id`, () => HttpResponse.json(current)),
  );
  return {
    posts,
    /** Moves the booking to its next state and announces it on the event stream. */
    advance() {
      const next = states.shift();
      if (!next) throw new Error("no more states");
      current = next;
      act(() => {
        FakeEventSource.open(`/bookings/${next.id}/events`)?.emit("status", {
          booking_id: next.id,
          status: next.status,
          version: next.version,
        });
      });
    },
  };
}

/** The traveler is someone else: empties the fields filled from the account. */
async function anotherPerson(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Viaja otra persona" }));
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await anotherPerson(user);
  await user.selectOptions(await screen.findByLabelText("Tratamiento"), "ms");
  await user.type(screen.getByLabelText("Nombre"), "Ana");
  await user.type(screen.getByLabelText("Apellido"), "Muñoz");
  await user.click(screen.getByLabelText("Femenino"));
  await user.type(screen.getByLabelText("Día"), "20");
  await user.type(screen.getByLabelText("Mes"), "5");
  await user.type(screen.getByLabelText("Año"), "1990");
  await user.type(screen.getByLabelText("Email"), "ana.prueba@example.com");
  await user.type(screen.getByRole("textbox", { name: "Teléfono" }), "300 123 4567");
  await user.type(screen.getByLabelText("Número de tarjeta"), "4242 4242 4242 4242");
  await user.type(screen.getByLabelText("Titular"), "ANA MUNOZ");
  await user.type(screen.getByLabelText("Vencimiento"), "12/30");
  await user.type(screen.getByLabelText("Código"), "123");
  await user.click(screen.getByRole("checkbox", { name: /Acepto las condiciones/ }));
}

const confirmButton = () =>
  screen.getAllByRole("button", { name: /Confirmar y pagar 230,01 USD/ })[0] as HTMLElement;

beforeEach(async () => {
  await signInForTests();
  // Only the clock is faked: the fixture's offers are valid until 21:26 UTC.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(FIXTURE_NOW);
  installFakeEventSource();
});

describe("passengers and payment", () => {
  it("shows the form for the flight of the trip, with its price", async () => {
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByRole("heading", { name: "Pasajeros y pago" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pasajero 1 · Adulto" })).toBeInTheDocument();
    expect(screen.getByText("Esta oferta no pide pasaporte.")).toBeInTheDocument();
    expect(screen.getByText(/Reservar ahora y pagar después · próximamente/)).toBeInTheDocument();
    const summary = screen.getByRole("complementary", { name: "Resumen" });
    expect(within(summary).getByText(/Basic/)).toBeInTheDocument();
    expect(confirmButton()).toBeEnabled();
  });

  it("shows every problem before sending anything", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    await screen.findByRole("heading", { name: "Pasajeros y pago" });
    await anotherPerson(user);
    await user.click(confirmButton());

    expect(await screen.findByText("Elige el tratamiento.")).toBeInTheDocument();
    expect(screen.getByText("Escribe el apellido.")).toBeInTheDocument();
    expect(screen.getByText("Revisa la fecha de nacimiento.")).toBeInTheDocument();
    expect(screen.getByText("Revisa el número de tarjeta.")).toBeInTheDocument();
    expect(screen.getByLabelText("Apellido")).toHaveAttribute("aria-invalid", "true");
  });

  it("clears the date error as soon as day, month and year make a valid date", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);
    await screen.findByRole("heading", { name: "Pasajeros y pago" });
    await user.click(confirmButton());
    expect(await screen.findByText("Revisa la fecha de nacimiento.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Día"), "20");
    await user.type(screen.getByLabelText("Mes"), "5");
    await user.type(screen.getByLabelText("Año"), "1990");

    await waitFor(() => expect(screen.queryByText("Revisa la fecha de nacimiento.")).not.toBeInTheDocument());
  });

  it("warns how the airline gets accented names and counts the 40 characters", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    await anotherPerson(user);
    await user.type(await screen.findByLabelText("Nombre"), "José");
    await user.type(screen.getByLabelText("Apellido"), "Muñoz");

    expect(screen.getByRole("status")).toHaveTextContent("A la aerolínea se envía como JOSE MUNOZ");
    expect(screen.getByText("9 / 40")).toBeInTheDocument();
  });

  it("books, follows the events and shows the confirmation", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const apiMock = bookingApi(bookings.pending, [bookings.processing, bookings.confirmed]);
    renderApp(`/checkout/${item.itemKey}`);
    await fillValidForm(user);

    await user.click(confirmButton());

    expect(await screen.findAllByText(/Confirmando con la aerolínea/)).not.toHaveLength(0);
    const [post] = apiMock.posts;
    expect(post?.key).toMatch(/^[0-9a-f-]{36}$/);
    expect(post?.body.payment_token).toBe("tok_fake_4242");
    expect(post?.body.passenger.traveller.phone_number).toBe("+573001234567");
    expect(JSON.stringify(post?.body)).not.toContain("4242 4242");

    apiMock.advance();
    apiMock.advance();

    expect(await screen.findByText("Reserva confirmada y pagada")).toBeInTheDocument();
    expect(screen.getByText("M6BM7T")).toBeInTheDocument();
    await waitFor(() => expect(useTrip.getState().order).toEqual([]));
    expect(FakeEventSource.instances.every((s) => s.closed)).toBe(true);
  });

  it("asks to approve a new price before charging, and continues once accepted", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const apiMock = bookingApi(bookings.pending, [bookings.awaitingPrice, bookings.confirmed]);
    const decisions: unknown[] = [];
    server.use(
      http.post(`${BOOKINGS}/:id/price-decision`, async ({ request }) => {
        decisions.push(await request.json());
        return HttpResponse.json({ ...bookings.pending, version: 4 }, { status: 202 });
      }),
    );
    renderApp(`/checkout/${item.itemKey}`);
    await fillValidForm(user);
    await user.click(confirmButton());
    await screen.findAllByText(/Confirmando con la aerolínea/);

    apiMock.advance();

    const dialog = await screen.findByRole("dialog", { name: "La aerolínea actualizó el precio de Basic" });
    expect(within(dialog).getByText("230,01 USD")).toBeInTheDocument();
    expect(within(dialog).getByText("267,67 USD")).toBeInTheDocument();
    expect(within(dialog).getByText(/Subió/)).toHaveTextContent("Subió 37,66 USD");

    await user.click(within(dialog).getByRole("button", { name: "Aceptar y continuar" }));
    expect(decisions).toEqual([{ decision: "accept", price: { amount: "267.67", currency: "USD" } }]);

    apiMock.advance();
    expect(await screen.findByText("Reserva confirmada y pagada")).toBeInTheDocument();
  });

  it("a declined card goes to the confirmation screen, and trying again uses a new key", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const apiMock = bookingApi(bookings.pending, [bookings.failedDeclined]);
    renderApp(`/checkout/${item.itemKey}`);
    await fillValidForm(user);
    await user.click(confirmButton());
    await screen.findAllByText(/Confirmando con la aerolínea/);

    apiMock.advance();

    expect(await screen.findByText("La tarjeta fue rechazada.")).toBeInTheDocument();
    expect(useCheckout.getState().attempts[item.itemKey]).toBeUndefined();
    await user.click(screen.getByRole("link", { name: "Probar con otra tarjeta" }));
    await user.type(await screen.findByLabelText("Número de tarjeta"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Vencimiento", { selector: "#cardExpiry" }), "12/30");
    await user.type(screen.getByLabelText("Código"), "123");
    await user.type(screen.getByLabelText("Titular"), "ANA MUNOZ");
    await user.click(confirmButton());
    await waitFor(() => expect(apiMock.posts).toHaveLength(2));
    expect(apiMock.posts[1]?.key).not.toBe(apiMock.posts[0]?.key);
  });

  it("an issuance error goes to the confirmation screen and keeps the attempt, so it can't be booked twice", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const issuanceError = { ...bookings.processing, status: "issuance_error", version: 4 } as Booking;
    const apiMock = bookingApi(bookings.pending, [issuanceError]);
    renderApp(`/checkout/${item.itemKey}`);
    await fillValidForm(user);
    await user.click(confirmButton());
    await screen.findAllByText(/Confirmando con la aerolínea/);

    apiMock.advance();

    expect(await screen.findByText("Error de emisión")).toBeInTheDocument();
    expect(useCheckout.getState().attempts[item.itemKey]?.bookingId).toBe(bookings.pending.id);
    expect(useTrip.getState().order).toEqual([item.itemKey]);
  });

  it("a retry after a network error sends the same Idempotency-Key", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const keys: (string | null)[] = [];
    server.use(
      http.post(BOOKINGS, ({ request }) => {
        keys.push(request.headers.get("Idempotency-Key"));
        return keys.length === 1
          ? HttpResponse.error()
          : HttpResponse.json(bookings.pending, { status: 202 });
      }),
      http.get(`${BOOKINGS}/:id`, () => HttpResponse.json(bookings.pending)),
    );
    renderApp(`/checkout/${item.itemKey}`);
    await fillValidForm(user);

    await user.click(confirmButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos enviar la reserva");
    await user.click(confirmButton());

    await waitFor(() => expect(keys).toHaveLength(2));
    expect(keys[1]).toBe(keys[0]);
  });

  it("keeps the passenger data, but not the card, if the traveler leaves and comes back", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    const first = renderApp(`/checkout/${item.itemKey}`);
    await anotherPerson(user);
    await user.type(await screen.findByLabelText("Apellido"), "Muñoz");
    await user.type(screen.getByLabelText("Número de tarjeta"), "4242");
    first.unmount();

    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByLabelText("Apellido")).toHaveValue("Muñoz");
    expect(screen.getByLabelText("Número de tarjeta")).toHaveValue("");
    expect(sessionStorage.getItem("booking-system.checkout")).not.toContain("4242");
  });

  it("blocks paying once the fare expired and points back to the trip", async () => {
    const item = addFlightToTrip();
    vi.setSystemTime(new Date(new Date(item.fare.expires_at).getTime() + 1000));
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByText("El precio de esta tarifa venció")).toBeInTheDocument();
    expect(confirmButton()).toBeDisabled();
    expect(screen.getByRole("link", { name: "Vuelve a Tu viaje" })).toBeInTheDocument();
  });
});

describe("passengers and payment with a session", () => {
  it("fills the passenger with the account, as the airline takes it, until someone else travels", async () => {
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByLabelText("Nombre")).toHaveValue("PEPE");
    expect(screen.getByLabelText("Apellido")).toHaveValue("PEREZ");
    expect(screen.getByLabelText("Email")).toHaveValue("pepe.perez@ejemplo.com");
    expect(screen.getByRole("note")).toHaveTextContent("Completamos con los datos de tu cuenta");

    await anotherPerson(user);

    expect(screen.getByLabelText("Nombre")).toHaveValue("");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("fills the phone of the account, which isn't in the token", async () => {
    server.use(
      http.get("*/api/v1/me", () => HttpResponse.json({ ...TEST_ME, phone_number: "+573105826464" })),
    );
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByDisplayValue("3105826464")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/\+57/)).toBeInTheDocument();

    await anotherPerson(user);

    expect(screen.queryByDisplayValue("3105826464")).not.toBeInTheDocument();
  });

  it("fills title, date of birth and gender from the last booking for themselves", async () => {
    server.use(
      http.get("*/api/v1/me", () =>
        HttpResponse.json({
          ...TEST_ME,
          traveller_profile: { title: "mr", born_on: "1990-08-23", gender: "m" },
        }),
      ),
    );
    const user = userEvent.setup();
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByDisplayValue("1990")).toBeInTheDocument();
    expect(screen.getByDisplayValue("23")).toBeInTheDocument();
    expect(screen.getByLabelText("Tratamiento")).toHaveValue("mr");
    expect(screen.getByRole("radio", { name: "Masculino" })).toBeChecked();

    await anotherPerson(user);

    expect(screen.queryByDisplayValue("1990")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Masculino" })).not.toBeChecked();
  });

  it("never shows the draft of another user who used this tab", async () => {
    const item = addFlightToTrip();
    const { cardNumber, cardHolder, cardExpiry, cardCode, ...empty } = EMPTY_VALUES;
    useCheckout.setState({
      owner: "otro-usuario",
      drafts: {
        [item.itemKey]: { ...empty, givenName: "MARIA", familyName: "LOPEZ", email: "m.lopez@keycloak.com" },
      },
      holders: { [item.itemKey]: false },
    });
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByLabelText("Nombre")).toHaveValue("PEPE");
    expect(screen.getByRole("button", { name: "Viaja otra persona" })).toBeInTheDocument();
    expect(useCheckout.getState().owner).toBe(TEST_USER.sub);
  });

  it("keeps that the user travels across a reload", async () => {
    const item = addFlightToTrip();
    const { cardNumber, cardHolder, cardExpiry, cardCode, ...empty } = EMPTY_VALUES;
    useCheckout.setState({
      owner: TEST_USER.sub,
      drafts: { [item.itemKey]: { ...empty, givenName: "PEPE", familyName: "PEREZ", birthYear: "1980" } },
      holders: { [item.itemKey]: true },
    });
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByDisplayValue("1980")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Viaja otra persona" })).toBeInTheDocument();
  });

  it("forgets every draft when the user signs out", async () => {
    const item = addFlightToTrip();
    useCheckout.getState().ownBy(TEST_USER.sub);
    useCheckout.getState().saveDraft(item.itemKey, { ...EMPTY_VALUES, givenName: "PEPE" });

    await clearSession("signed_out");

    expect(useCheckout.getState().drafts).toEqual({});
  });

  it("without a session goes to the sign in, with the trip saved", async () => {
    await clearSession("signed_out");
    const item = addFlightToTrip();
    renderApp(`/checkout/${item.itemKey}`);

    expect(await screen.findByRole("heading", { name: "Ingresa para reservar" })).toBeInTheDocument();
    expect(screen.getByText("Tu viaje queda guardado mientras ingresas.")).toBeInTheDocument();
  });
});
