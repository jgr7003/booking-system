import { Link, useParams } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { isFinal, useBooking, useBookingEvents } from "@/api/bookings";
import { ApiError } from "@/api/client";
import { TopBar } from "@/components/layout/TopBar";
import { Confirmed } from "./Confirmed";
import { Confirming } from "./Confirming";
import { Failed } from "./Failed";
import { IssuanceError } from "./IssuanceError";
import { CARD } from "./styles";

/** Design board "Confirmación" (Propuesta A v2) and its states. */
export function BookingPage() {
  const { bookingId } = useParams({ from: "/bookings/$bookingId" });
  const { data: booking, error } = useBooking(bookingId);
  useBookingEvents(booking && isFinal(booking.status) ? null : bookingId);

  let content: ReactNode;
  if (error instanceof ApiError && error.status === 404) content = <NotFound />;
  else if (!booking) content = <Confirming />;
  else if (booking.status === "confirmed" && booking.order && booking.booking_reference)
    content = <Confirmed booking={booking} order={booking.order} reference={booking.booking_reference} />;
  else if (booking.status === "issuance_error") content = <IssuanceError booking={booking} />;
  else if (booking.status === "failed" || booking.status === "cancelled")
    content = <Failed booking={booking} />;
  else content = <Confirming booking={booking} />;

  return (
    <>
      <TopBar className="min-h-[56px] justify-between sm:min-h-[60px]">
        <span className="flex-1" />
        {/* There is no list of bookings yet: it comes with user accounts. */}
        <span
          aria-disabled="true"
          className="inline-flex shrink-0 items-center gap-2 text-[13px] whitespace-nowrap text-line-strong sm:text-[14px]"
        >
          Mis reservas
          <span className="rounded border border-muted-2 px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.04em] uppercase sm:text-[11px]">
            Pronto
          </span>
        </span>
      </TopBar>
      <main className="mx-auto flex max-w-[1160px] flex-col gap-3.5 px-3 pt-4 pb-16 sm:gap-5 sm:px-5 sm:pt-7">
        {content}
      </main>
    </>
  );
}

function NotFound() {
  return (
    <section role="status" className={`${CARD} flex flex-col items-center gap-2 p-8 text-center`}>
      <h1 className="text-[20px] font-bold">No encontramos esta reserva</h1>
      <p className="text-ink-2">Revisá el link o buscá tu viaje de nuevo.</p>
      <Link to="/trip" className="font-semibold">
        Ir a Tu viaje
      </Link>
    </section>
  );
}
