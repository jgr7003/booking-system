import { Link } from "@tanstack/react-router";
import type { Fare, Flight } from "@/api/client";
import { AirlineBadge } from "@/components/flight/AirlineBadge";
import { SliceTimeline } from "@/components/flight/SliceTimeline";
import { Dialog } from "@/components/ui/dialog";
import { flightNumbersOf } from "@/lib/flights/itinerary";
import type { FlightSearch } from "@/lib/flights/search";
import { useExpiry } from "@/lib/useExpiry";
import { FareMatrix } from "./FareMatrix";
import type { FlightInsight } from "./logic";

interface FaresDialogProps {
  flight: Flight | undefined;
  insight: FlightInsight | undefined;
  search: FlightSearch;
  onChoose: (flight: Flight, fare: Fare) => void;
  onClose: () => void;
}

/**
 * Fares of a flight in a modal: the flight on top, then the matrix to compare and choose.
 *
 * Opening it only renders this dialog; the list of results behind it doesn't change.
 */
export function FaresDialog({ flight, insight, search, onChoose, onClose }: FaresDialogProps) {
  // Expired fares can't be chosen: the dialog closes and the "precios vencidos" one takes over.
  const faresExpiry = useExpiry(flight?.fares[0]?.expires_at);
  const expired = flight !== undefined && faresExpiry.expired;
  return (
    <Dialog
      open={flight !== undefined && !expired}
      onClose={onClose}
      title={flight ? `Tarifas de ${flight.owner.name}` : ""}
      flush
      className="w-[min(1040px,calc(100vw-24px))] gap-3.5"
    >
      {flight && (
        <>
          <div className="flex flex-col gap-1 px-5">
            <span className="flex items-center gap-2 text-[13px] text-muted">
              <AirlineBadge code={flight.owner.code} />
              {flight.owner.name} · <span className="data">{flightNumbersOf(flight)}</span>
            </span>
            {flight.slices.map((slice, i) => (
              <SliceTimeline
                key={`${slice.origin.code}-${slice.destination.code}`}
                slice={slice}
                label={flight.slices.length > 1 ? (i === 0 ? "Ida" : "Vuelta") : undefined}
              />
            ))}
          </div>
          <div className="overflow-x-auto border-y border-action-line bg-action-tint px-2 pt-3.5 pb-[18px] sm:px-5">
            <FareMatrix fares={flight.fares} onChoose={(fare) => onChoose(flight, fare)} />
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-5 pb-4 text-[12px] text-muted">
            <span>{insight?.note}</span>
            <Link
              to="/flights/$key"
              params={{ key: flight.key }}
              search={{ ...search, fare: flight.fares[0]?.offer_id }}
              className="font-semibold"
            >
              Ver itinerario completo
            </Link>
          </div>
        </>
      )}
    </Dialog>
  );
}
