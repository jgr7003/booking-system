import { useEffect, useState } from "react";
import type { Booking } from "@/api/client";
import { cn } from "@/lib/cn";
import { formatDate, formatTotal } from "@/lib/format";
import { BeforeFlying } from "./BeforeFlying";
import { Included } from "./Included";
import { cityOf, isRoundTrip, localDate, type Order, passengerName, sliceDate } from "./logic";
import { Manage } from "./Manage";
import { SliceCard } from "./SliceCard";
import { CARD, KICKER } from "./styles";

export function Confirmed({
  booking,
  order,
  reference,
}: {
  booking: Booking;
  order: Order;
  reference: string;
}) {
  const roundTrip = isRoundTrip(order);
  const first = order.slices[0];
  const destination = roundTrip ? first?.destination : order.slices.at(-1)?.destination;
  const knownCities = Boolean(first?.origin.city && destination?.city);
  const passenger = passengerName(booking);
  const paidOn = order.paid_at ? localDate(order.paid_at) : null;

  return (
    <>
      <section aria-labelledby="status" className={`${CARD} overflow-hidden max-sm:contents`}>
        <div className="flex items-center gap-3 border-b border-ok-line bg-ok-soft px-6 py-3.5 max-sm:-mx-3 max-sm:-mt-4 max-sm:px-4 max-sm:py-3">
          <span className="inline-flex h-9 w-9 flex-none items-center justify-center rounded-full bg-ok text-white max-sm:h-[30px] max-sm:w-[30px]">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12.5l4.5 4.5L19 7.5" />
            </svg>
          </span>
          <div className="flex flex-col">
            <h1 id="status" className="text-[17px] font-bold text-ok-ink sm:text-[22px]">
              {order.awaiting_payment
                ? "Reserva confirmada · pendiente de pago"
                : "Reserva confirmada y pagada"}
            </h1>
            <span className="text-[13px] text-ok-ink-2 sm:hidden">
              {order.tickets.length ? "Tickets emitidos" : "Los tickets se emiten al pagar"}
              {paidOn && ` · ${paidOn.slice(4)}`}
            </span>
            <span className="text-[14px] text-ok-ink-2 max-sm:hidden">
              {paidOn ? (
                <>
                  Pagaste <strong className="font-mono">{formatTotal(booking.price)}</strong> el {paidOn}.
                </>
              ) : (
                <>
                  Total <strong className="font-mono">{formatTotal(booking.price)}</strong>.
                </>
              )}{" "}
              {order.tickets.length ? "Los tickets ya están emitidos." : "Los tickets se emiten al pagar."}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-5 px-6 py-[22px] max-sm:flex-col-reverse max-sm:items-stretch max-sm:gap-3.5 max-sm:p-0">
          <div className="flex min-w-0 flex-col gap-2 max-sm:gap-1 max-sm:px-1">
            <span className={`${KICKER} max-sm:text-[11px]`}>
              {roundTrip ? "Ida y vuelta" : "Solo ida"} · 1 pasajero
            </span>
            <span className="flex flex-wrap items-center gap-3 text-[24px] font-bold tracking-[-0.01em] sm:text-[30px]">
              {first && cityOf(first.origin)}
              {roundTrip ? (
                <svg
                  width="26"
                  height="26"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  role="img"
                  aria-label="ida y vuelta"
                >
                  <path d="M4 8h16l-4-4M20 16H4l4 4" />
                </svg>
              ) : (
                <span>→</span>
              )}
              {destination && cityOf(destination)}
            </span>
            {!knownCities && first && destination && (
              <span className="text-[14px] text-ink-2">
                {first.origin.name} {roundTrip ? "⇄" : "→"} {destination.name}
              </span>
            )}
            <span className="flex flex-wrap gap-x-[18px] gap-y-1.5 text-[14px] text-ink-2 max-sm:flex-col max-sm:gap-1 sm:text-[15px]">
              {order.slices.map((slice, i) => (
                <span key={`${sliceDate(slice)}-${slice.origin.code}`}>
                  <strong className="text-ink">{i === 0 ? "Ida" : "Vuelta"}</strong>{" "}
                  {formatDate(sliceDate(slice))}
                </span>
              ))}
              <span>{passenger}</span>
            </span>
          </div>
          <ReferenceBox reference={reference} airline={order.owner.name} />
        </div>
      </section>

      <div className="flex flex-wrap items-start gap-5 max-sm:gap-3.5">
        <div className="flex min-w-0 flex-[999_1_620px] flex-col gap-4 max-sm:gap-3.5">
          <section aria-labelledby="itinerary" className="flex flex-col gap-3">
            <h2 id="itinerary" className="text-[16px] font-bold max-sm:mx-1 max-sm:mt-1.5 sm:text-[18px]">
              Itinerario{" "}
              <span className="text-[12px] font-normal text-muted sm:text-[13px]">
                · <span className="sm:hidden">hora local</span>
                <span className="max-sm:hidden">horarios en hora local de cada aeropuerto</span>
              </span>
            </h2>
            {order.slices.map((slice, i) => (
              <SliceCard
                key={`${sliceDate(slice)}-${slice.origin.code}`}
                slice={slice}
                label={roundTrip && i > 0 ? "VUELTA" : "IDA"}
              />
            ))}
          </section>
          <Included order={order} reference={reference} />
          <BeforeFlying
            passenger={passengerName(booking, false)}
            airline={order.owner.name}
            reference={reference}
          />
        </div>

        <aside className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-4 max-sm:max-w-none max-sm:gap-3.5">
          <section
            aria-labelledby="passenger"
            className={`${CARD} flex flex-col gap-2.5 px-[18px] py-4 max-sm:p-3.5`}
          >
            <h2 id="passenger" className={KICKER}>
              <span className="sm:hidden">Pasajero, ticket y pago</span>
              <span className="max-sm:hidden">Pasajero y ticket</span>
            </h2>
            <div className="flex items-baseline justify-between gap-2.5">
              <strong className="text-[14px] sm:text-[16px]">{passenger}</strong>
              <span className="text-[13px] text-muted">Adulto</span>
            </div>
            <div className="flex justify-between text-[14px]">
              <span className="text-ink-2">Ticket electrónico</span>
              <span className="font-mono font-semibold">
                {order.tickets.length ? order.tickets.map((t) => t.number).join(", ") : "Se emiten al pagar"}
              </span>
            </div>
            <div className="contents sm:hidden">
              <PaymentRows booking={booking} order={order} paidOn={paidOn} />
            </div>
          </section>
          <section
            aria-labelledby="payment"
            className={`${CARD} flex flex-col gap-2.5 px-[18px] py-4 max-sm:hidden`}
          >
            <h2 id="payment" className={KICKER}>
              Pago
            </h2>
            <PaymentRows booking={booking} order={order} paidOn={paidOn} showStatus />
          </section>
          <Manage order={order} reference={reference} />
        </aside>
      </div>
    </>
  );
}

function PaymentRows({
  booking,
  order,
  paidOn,
  showStatus = false,
}: {
  booking: Booking;
  order: Order;
  paidOn: string | null;
  showStatus?: boolean;
}) {
  return (
    <>
      {showStatus && (
        <div className="flex justify-between text-[14px]">
          <span className="text-ink-2">Estado</span>
          <span className={cn("font-semibold", order.awaiting_payment ? "text-warn" : "text-ok")}>
            {order.awaiting_payment ? "Pendiente de pago" : "Pagado"}
          </span>
        </div>
      )}
      {paidOn && (
        <div className="flex justify-between text-[14px]">
          <span className="text-ink-2">{showStatus ? "Fecha" : "Pagado"}</span>
          <span className="font-mono">{paidOn.slice(4)}</span>
        </div>
      )}
      <div className="flex justify-between text-[14px]">
        <span className="text-ink-2">Vendido por</span>
        <span>{order.owner.name}</span>
      </div>
      <div className="flex items-baseline justify-between border-t border-line-soft pt-2.5">
        <strong>Total cobrado</strong>
        <span className="font-mono text-[22px] font-semibold">{formatTotal(booking.price)}</span>
      </div>
    </>
  );
}

function ReferenceBox({ reference, airline }: { reference: string; airline: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);
  return (
    <div className="flex items-center gap-[18px] rounded-lg border-2 border-ink bg-white px-[18px] py-3.5 max-sm:flex-col max-sm:gap-1.5 max-sm:p-4 max-sm:text-center">
      <div className="flex flex-col gap-0.5">
        <span className="text-[11px] font-semibold tracking-[0.08em] text-muted uppercase sm:text-[12px]">
          Código de reserva
        </span>
        <span className="font-mono text-[44px] leading-[1.1] font-semibold tracking-[0.14em] sm:text-[40px]">
          {reference}
        </span>
        <span className="text-[12px] text-muted">Lo pide {airline} para el check-in</span>
      </div>
      <button
        type="button"
        aria-live="polite"
        onClick={() => {
          navigator.clipboard?.writeText(reference).then(() => setCopied(true));
        }}
        className={cn(
          "h-11 min-w-24 flex-none rounded-md px-4 text-[14px] font-semibold",
          copied ? "border border-ok bg-ok-soft text-ok" : "bg-action text-white",
        )}
      >
        {copied ? "✓ Copiado" : "Copiar"}
      </button>
    </div>
  );
}
