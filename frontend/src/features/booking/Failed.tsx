import { Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import type { Booking } from "@/api/client";
import { tripItems, useTrip } from "@/features/trip/public";
import { pickSearch } from "@/lib/flights/search";
import { formatDate, formatTotal } from "@/lib/format";
import { cityOf, failureContent } from "./logic";
import { ProblemHeader } from "./ProblemHeader";
import { CARD } from "./styles";

const OUTLINE_LINK =
  "inline-flex h-12 items-center rounded-md border border-action px-[22px] font-semibold text-action";

export function Failed({ booking }: { booking: Booking }) {
  const content = failureContent(booking.failure_code, booking.status);
  // GET doesn't bring the order of a failed booking: the summary comes from "Tu viaje".
  const state = useTrip(useShallow((s) => ({ items: s.items, order: s.order })));
  const item = useMemo(
    () => tripItems(state).find((i) => i.fare.offer_id === booking.offer_id),
    [state, booking.offer_id],
  );
  const slices = item?.flight.slices ?? [];
  const first = slices[0];
  const roundTrip = slices.length > 1;

  return (
    <section role="alert" className={`${CARD} overflow-hidden`}>
      <ProblemHeader
        tone="bad"
        title="No pudimos completar tu reserva"
        subtitle={content.title}
        icon={
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M7 7l10 10M17 7L7 17" />
          </svg>
        }
      />
      <div className="flex flex-col gap-4 px-6 py-5 max-sm:px-4">
        <div className="flex items-center gap-3 rounded-md border border-ok-line bg-ok-soft px-4 py-3">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#0B6B44"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z" />
            <path d="M8.5 12.5l2.5 2.5 4.5-5" />
          </svg>
          <span className="text-[15px] text-ok-ink">
            <strong>No se cobró nada.</strong> Tu tarjeta no tiene ningún cargo por este intento.
          </span>
        </div>
        <p className="max-w-[760px] text-[16px] leading-normal text-ink-2">{content.body}</p>
        <div className="flex flex-wrap gap-2.5">
          <Link
            to="/trip"
            className="inline-flex h-12 items-center rounded-md bg-action px-[22px] font-semibold text-white hover:text-white"
          >
            Volver a Tu viaje
          </Link>
          {content.secondary && item && content.secondary.to === "checkout" && (
            <Link to="/checkout/$itemKey" params={{ itemKey: item.itemKey }} className={OUTLINE_LINK}>
              {content.secondary.label}
            </Link>
          )}
          {content.secondary && item && content.secondary.to === "results" && (
            <Link to="/flights" search={pickSearch(item.search)} className={OUTLINE_LINK}>
              {content.secondary.label}
            </Link>
          )}
        </div>
      </div>
      {item && first && (
        <div className="flex flex-wrap gap-x-6 gap-y-1.5 border-t border-line-soft bg-surface-2 px-6 py-3 text-[14px] text-ink-2 max-sm:px-4">
          <span>
            Intentaste reservar:{" "}
            <strong className="text-ink">
              {cityOf(first.origin)} {roundTrip ? "⇄" : "→"} {cityOf(first.destination)}
            </strong>{" "}
            · ida {formatDate(first.segments[0]?.departing_at ?? "", { year: !roundTrip })}
            {roundTrip && slices[1] && `, vuelta ${formatDate(slices[1].segments[0]?.departing_at ?? "")}`}
          </span>
          <span>
            {item.flight.owner.name} · {item.fare.slices[0]?.fare_brand ?? "Tarifa"} ·{" "}
            <strong className="font-mono text-ink">{formatTotal(booking.price)}</strong>
          </span>
        </div>
      )}
    </section>
  );
}
