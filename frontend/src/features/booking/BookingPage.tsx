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
      <TopBar className="min-h-[56px] sm:min-h-[60px]" />
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
      <p className="text-ink-2">Revisa el link o busca tu viaje de nuevo.</p>
      <Link to="/trip" className="font-semibold">
        Ir a Tu viaje
      </Link>
    </section>
  );
}
