import { Link, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { useMemo } from "react";
import type { Fare } from "@/api/client";
import { useFlightSearch } from "@/api/flights";
import { HeaderExpiry } from "@/components/layout/HeaderExpiry";
import { StepLinks } from "@/components/layout/Steps";
import { TopBar } from "@/components/layout/TopBar";
import { useAddToTrip } from "@/features/trip/public";
import { isComplete, pickSearch, toCriteria } from "@/lib/flights/search";
import { FareConditions } from "./FareConditions";
import { FareTable } from "./FareTable";
import { FlightHeading } from "./FlightHeading";
import { Itinerary } from "./Itinerary";
import { PriceAside } from "./PriceAside";

/** Design board "Detalle de la oferta". */
export function FlightDetailPage() {
  const { key } = useParams({ from: "/flights/$key" });
  const search = useSearch({ from: "/flights/$key" });
  const navigate = useNavigate({ from: "/flights/$key" });
  const complete = isComplete(search) ? search : null;
  const criteriaKey = JSON.stringify(complete ? pickSearch(complete) : null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: recomputed only when the criteria change.
  const criteria = useMemo(() => (complete ? toCriteria(complete) : null), [criteriaKey]);
  // Same query as the results page: comes from the cache, or searches again after a reload.
  const query = useFlightSearch(criteria);
  const addToTrip = useAddToTrip();
  const fromTrip = search.via === "trip";
  const flight = query.data?.flights.find((f) => f.key === key);
  const selected = flight
    ? (flight.fares.find((f) => f.offer_id === search.fare) ?? (flight.fares[0] as Fare))
    : null;

  const backLink = fromTrip ? (
    <Link to="/trip" className="text-[14px]">
      ← Volver a tu viaje
    </Link>
  ) : (
    <Link to="/flights" search={{ ...pickSearch(search), hl: key }} className="text-[14px]">
      ← Volver a resultados
    </Link>
  );

  return (
    <>
      <TopBar className="min-h-14 gap-x-4 gap-y-3">
        <span className="max-sm:hidden">
          <StepLinks current={fromTrip ? 1 : 0} />
        </span>
        <span className="flex-1 sm:hidden" />
        {selected && <HeaderExpiry expiresAt={selected.expires_at} />}
      </TopBar>

      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-5 px-3 pt-3.5 pb-28 sm:px-5 sm:pt-6 sm:pb-16">
        {!complete || query.isPending ? (
          <p className="text-muted">{complete ? "Cargando el vuelo…" : backLink}</p>
        ) : !flight || !selected ? (
          <section className="flex flex-col items-start gap-3">
            {backLink}
            <h1 className="text-[22px] font-bold">Este vuelo ya no está en los resultados</h1>
            <p className="text-ink-2">Las aerolíneas pueden retirar ofertas entre una búsqueda y otra.</p>
          </section>
        ) : (
          <>
            <div className="flex min-w-0 flex-[999_1_640px] flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                {backLink}
                <FlightHeading flight={flight} />
              </div>
              <Itinerary flight={flight} />
              <FareTable
                flight={flight}
                selected={selected}
                onSelect={(fare) =>
                  navigate({ search: (prev) => ({ ...prev, fare: fare.offer_id }), replace: true })
                }
              />
              <FareConditions flight={flight} fare={selected} />
            </div>
            <PriceAside
              flight={flight}
              fare={selected}
              search={search}
              onSave={() => complete && addToTrip(flight, selected, complete, query.data?.search_id ?? "")}
            />
          </>
        )}
      </main>
    </>
  );
}
