import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { isFinal, useBooking, useBookingEvents, useCreateBooking, usePriceDecision } from "@/api/bookings";
import { ApiError, type Booking } from "@/api/client";
import { SpinnerIcon } from "@/components/icons";
import { HeaderExpiry } from "@/components/layout/HeaderExpiry";
import { StepLinks } from "@/components/layout/Steps";
import { TopBar } from "@/components/layout/TopBar";
import { Notice } from "@/components/ui/notice";
import { SlowBookingNotice } from "@/features/booking/public";
import { type TripItem, useTrip } from "@/features/trip/public";
import { cn } from "@/lib/cn";
import { todayIso } from "@/lib/dates";
import { fareName } from "@/lib/flights/fares";
import { formatTotal } from "@/lib/format";
import { expiryOf } from "@/lib/useExpiry";
import { useNow } from "@/lib/useNow";
import { FlightSummary } from "./FlightSummary";
import {
  buildBookingRequest,
  type CheckoutValues,
  checkoutSchema,
  conditionsSummary,
  departureDateOf,
  draftOf,
  EMPTY_VALUES,
  failureMessage,
} from "./logic";
import { PassengerSection } from "./PassengerSection";
import { PaymentSection } from "./PaymentSection";
import { PriceChangedDialog } from "./PriceChangedDialog";
import { useCheckout } from "./store";

/** Design board "Pasajeros y pago", for one flight of "Tu viaje". */
export function CheckoutPage() {
  const { itemKey } = useParams({ from: "/checkout/$itemKey" });
  const item = useTrip((s) => s.items[itemKey]);
  if (!item) return <MissingItem />;
  return <Checkout item={item} />;
}

/** What the traveler sees after a booking that didn't go through. */
interface Outcome {
  title: string;
  body: string;
  backToTrip: boolean;
}

function Checkout({ item }: { item: TripItem }) {
  const { itemKey, fare, flight } = item;
  const navigate = useNavigate();
  const removeItem = useTrip((s) => s.remove);
  const draft = useCheckout((s) => s.drafts[itemKey]);
  const attempt = useCheckout((s) => s.attempts[itemKey]);
  const { saveDraft, attemptFor, setBooking, endAttempt, forget } = useCheckout.getState();
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  const now = useNow(1000);
  const { expired } = expiryOf(fare.expires_at, now);
  const departureDate = departureDateOf(flight);
  const today = todayIso(now);
  const schema = useMemo(
    () => checkoutSchema({ departureDate, requiresPassport: fare.requires_identity_documents, today }),
    [departureDate, fare.requires_identity_documents, today],
  );
  const form = useForm<CheckoutValues>({
    defaultValues: { ...EMPTY_VALUES, ...draft },
    resolver: zodResolver(schema),
  });

  // The typed data survives an expired fare or a reload (design board "Estados"); the card doesn't.
  useEffect(() => {
    const subscription = form.watch((values) =>
      saveDraft(itemKey, draftOf({ ...EMPTY_VALUES, ...values } as CheckoutValues)),
    );
    return () => subscription.unsubscribe();
  }, [form, itemKey, saveDraft]);

  // A booking of another offer (the fare was refreshed) isn't this checkout's.
  const bookingId = attempt?.offerId === fare.offer_id ? (attempt.bookingId ?? null) : null;
  const { data: booking } = useBooking(bookingId);
  useBookingEvents(booking && isFinal(booking.status) ? null : bookingId);
  const create = useCreateBooking();
  const decision = usePriceDecision(bookingId ?? "");

  useEffect(() => {
    if (!booking) return;
    if (booking.status === "confirmed") {
      // Leave first: removing the item before would show "this flight is no longer in your trip".
      navigate({ to: "/bookings/$bookingId", params: { bookingId: booking.id }, replace: true }).then(() => {
        forget(itemKey);
        removeItem(itemKey);
      });
    } else if (booking.status === "failed") {
      // The confirmation screen explains it (state 5); the flight stays in the trip to retry.
      endAttempt(itemKey);
      navigate({ to: "/bookings/$bookingId", params: { bookingId: booking.id } });
    } else if (booking.status === "issuance_error") {
      // The attempt is NOT ended: the airline may have issued this booking, so a new attempt for the
      // same flight could duplicate it. A reload or a return here lands on the same booking.
      navigate({ to: "/bookings/$bookingId", params: { bookingId: booking.id } });
    } else if (booking.status === "cancelled") {
      // The traveler rejected a new price here: it's resolved on this screen.
      setOutcome(outcomeOf(booking));
      endAttempt(itemKey);
    }
  }, [booking, itemKey, forget, removeItem, endAttempt, navigate]);

  const processing =
    create.isPending ||
    (booking !== undefined && (booking.status === "pending" || booking.status === "processing"));

  async function submit(values: CheckoutValues) {
    setOutcome(null);
    // Same attempt, same key: a double click or a retry after a network error books once.
    const { idempotencyKey } = attemptFor(itemKey, fare.offer_id);
    try {
      const created = await create.mutateAsync({ body: buildBookingRequest(values, fare), idempotencyKey });
      setBooking(itemKey, created.id);
    } catch (error) {
      setOutcome(
        error instanceof ApiError && error.status < 500
          ? {
              title: "No pudimos enviar la reserva",
              body: "Revisá los datos e intentá de nuevo.",
              backToTrip: false,
            }
          : {
              title: "No pudimos enviar la reserva",
              body: "Probá de nuevo: no se reserva dos veces.",
              backToTrip: false,
            },
      );
    }
  }

  const price = fare.price.total;
  const submitLabel = processing
    ? "Confirmando con la aerolínea…"
    : `Confirmar y pagar ${formatTotal(price)}`;
  const submitButton = (className: string) => (
    <button
      type="submit"
      form="checkout"
      disabled={processing || expired}
      className={cn(
        "inline-flex h-12 items-center justify-center gap-2 rounded-md bg-action font-semibold text-white disabled:bg-subtle",
        className,
      )}
    >
      {processing && <SpinnerIcon width={18} height={18} className="animate-spin" />}
      {submitLabel}
    </button>
  );

  return (
    <>
      <TopBar>
        <span className="max-sm:hidden flex-1">
          <StepLinks current={2} />
        </span>
        <strong className="flex-1 text-[16px] sm:hidden">Pasajero 1 · Adulto</strong>
        <span className="max-sm:hidden">
          <HeaderExpiry expiresAt={fare.expires_at} />
        </span>
        <span className="sm:hidden">
          <HeaderExpiry expiresAt={fare.expires_at} compact />
        </span>
      </TopBar>

      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-5 px-3.5 pt-3.5 pb-28 sm:px-5 sm:pt-6 sm:pb-16">
        <form
          id="checkout"
          noValidate
          onSubmit={form.handleSubmit(submit)}
          className="flex min-w-0 flex-[999_1_640px] flex-col gap-4"
        >
          <h1 className="text-[22px] font-bold max-sm:hidden sm:text-[28px]">Pasajeros y pago</h1>

          {expired && (
            <Notice tone="warn" title="El precio de esta tarifa venció">
              Los datos que cargaste quedan guardados.{" "}
              <Link to="/trip" className="font-semibold">
                Volvé a Tu viaje
              </Link>{" "}
              para actualizar el precio.
            </Notice>
          )}
          {outcome && (
            <Notice tone="bad" title={outcome.title}>
              {outcome.body}{" "}
              {outcome.backToTrip && (
                <Link to="/trip" className="font-semibold">
                  Volver a Tu viaje
                </Link>
              )}
            </Notice>
          )}
          {processing && (
            <p
              role="status"
              className="flex items-center gap-2 rounded-lg border border-action-line bg-action-tint px-4 py-3 text-[14px]"
            >
              <SpinnerIcon width={18} height={18} className="animate-spin text-action" />
              Reconfirmamos el precio con la aerolínea y emitimos el ticket. Tarda unos segundos.
            </p>
          )}
          {processing && booking && <SlowBookingNotice createdAt={booking.created_at} />}

          <fieldset disabled={processing} className="flex min-w-0 flex-col gap-4">
            <PassengerSection form={form} fare={fare} departureDate={departureDate} />
            <PaymentSection form={form} fare={fare} airline={flight.owner.name} />
            <label className="flex items-start gap-2.5 text-[14px]">
              <input
                type="checkbox"
                {...form.register("acceptConditions")}
                aria-invalid={!!form.formState.errors.acceptConditions}
                className="mt-0.5 h-[18px] w-[18px] shrink-0 accent-action"
              />
              <span>
                Acepto las condiciones de {fareName(fare)} ({conditionsSummary(fare)}) y las{" "}
                {flight.owner.conditions_of_carriage_url ? (
                  <a href={flight.owner.conditions_of_carriage_url} target="_blank" rel="noreferrer">
                    condiciones de transporte de {flight.owner.name}
                  </a>
                ) : (
                  `condiciones de transporte de ${flight.owner.name}`
                )}
                .
              </span>
            </label>
            {form.formState.errors.acceptConditions && (
              <span className="-mt-2 text-[12px] text-bad">
                {form.formState.errors.acceptConditions.message}
              </span>
            )}
          </fieldset>
        </form>

        <FlightSummary item={item}>
          {submitButton("max-sm:hidden")}
          <p className="text-[12px] leading-[1.45] text-muted">
            Al confirmar se vuelve a consultar la oferta. Si el precio cambió, se muestra la diferencia y se
            pide aprobarla antes de cobrar.
          </p>
        </FlightSummary>
      </main>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-white px-3.5 pt-3 pb-[22px] sm:hidden">
        {submitButton("w-full h-[50px] text-[15px]")}
      </div>

      {booking?.status === "awaiting_price_approval" && booking.offered_price && (
        <PriceChangedDialog
          open
          fareName={fareName(fare)}
          before={booking.price}
          now={booking.offered_price}
          busy={decision.isPending}
          onAccept={() =>
            decision.mutate({ decision: "accept", price: booking.offered_price as Booking["price"] })
          }
          onReject={() =>
            decision.mutate({ decision: "reject", price: booking.offered_price as Booking["price"] })
          }
        />
      )}
    </>
  );
}

function outcomeOf(booking: Booking): Outcome {
  if (booking.status === "cancelled") {
    return {
      title: "No se hizo la reserva",
      body: "No aceptaste el precio nuevo, así que no se cobró nada. En Tu viaje podés actualizar el precio o elegir otra tarifa.",
      backToTrip: true,
    };
  }
  return failureMessage(booking.failure_code);
}

function MissingItem() {
  return (
    <>
      <TopBar />
      <main className="mx-auto flex max-w-[640px] flex-col gap-3 px-4 py-10 text-center">
        <h1 className="text-[22px] font-bold">Este vuelo ya no está en tu viaje</h1>
        <p className="text-ink-2">Puede que ya lo hayas reservado o que lo hayas quitado.</p>
        <Link to="/trip" className="font-semibold">
          Ir a Tu viaje
        </Link>
      </main>
    </>
  );
}
