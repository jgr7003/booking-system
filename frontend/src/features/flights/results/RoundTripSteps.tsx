import { useNavigate } from "@tanstack/react-router";
import { useCallback, useMemo } from "react";
import type { Flight } from "@/api/client";
import { AirlineBadge } from "@/components/flight/AirlineBadge";
import { SliceTimeline } from "@/components/flight/SliceTimeline";
import { flightNumbersOf } from "@/lib/flights/itinerary";
import { formatDate } from "@/lib/format";
import { FlightCard } from "./FlightCard";
import { flightInsights, groupByOutbound, returnView, type SortKey, sortFlights } from "./logic";

interface RoundTripStepsProps {
  /** Every combination (outbound + return), already filtered and sorted. */
  flights: Flight[];
  /** Key of the chosen outbound (`out` in the URL), if any. */
  selectedOutbound: string | undefined;
  /** "1 adulto", for the price captions. */
  passengers: string;
  currency: string | undefined;
  /** Order of the list, also applied to the returns (sorting combinations by departure only sees the outbound). */
  sort: SortKey | undefined;
  /** Opens the fares of a combination. */
  onOpenFares: (key: string) => void;
}

/**
 * A round trip in two steps: each outbound once, then only the returns of the chosen one.
 *
 * The search is still a round trip (combined fares are usually cheaper than two one-ways); this
 * only avoids drawing a card per combination (e.g. 61 outbounds × 56 returns = 1,744 cards).
 */
export function RoundTripSteps({
  flights,
  selectedOutbound,
  passengers,
  currency,
  sort,
  onOpenFares,
}: RoundTripStepsProps) {
  const navigate = useNavigate({ from: "/flights" });
  const outbounds = useMemo(() => groupByOutbound(flights), [flights]);
  const selected = outbounds.find((o) => o.key === selectedOutbound);

  const selectOutbound = useCallback(
    (key: string) => {
      navigate({ search: (prev) => ({ ...prev, out: key, hl: undefined }) });
      window.scrollTo({ top: 0 });
    },
    [navigate],
  );

  const outboundCards = useMemo(() => outbounds.map((o) => o.flight), [outbounds]);
  const outboundInsights = useMemo(() => flightInsights(outboundCards), [outboundCards]);
  const returnCards = useMemo(
    () => (selected ? sortFlights(selected.returns.map(returnView), sort) : []),
    [selected, sort],
  );
  const returnInsights = useMemo(() => flightInsights(returnCards), [returnCards]);
  const priceNote = `precio total ida y vuelta por ${passengers}, con impuestos${currency ? `, en ${currency}` : ""}`;

  if (!selected) {
    const first = outbounds[0]?.flight.slices[0];
    return (
      <section aria-labelledby="step-outbound" className="flex flex-col gap-3">
        <StepHeading id="step-outbound" step={1} title="Elige tu ida">
          {first &&
            `${first.origin.city ?? first.origin.code} → ${first.destination.city ?? first.destination.code}`}
          {first?.segments[0] && ` · ${formatDate(first.segments[0].departing_at)}`}
        </StepHeading>
        <p className="text-[13px] text-muted" aria-live="polite">
          {outbounds.length} {outbounds.length === 1 ? "ida" : "idas"} · {priceNote}. Al elegir una, ves sus
          vueltas.
        </p>
        <div className="flex flex-col gap-4 pt-1">
          {outbounds.map((outbound) => (
            <FlightCard
              key={outbound.key}
              flight={outbound.flight}
              insight={outboundInsights.get(outbound.key)}
              onSelect={selectOutbound}
              opensDialog={false}
              priceCaption="Ida y vuelta desde"
              actionLabel={`${outbound.returns.length} ${outbound.returns.length === 1 ? "vuelta" : "vueltas"}`}
              sliceLabels={["Ida"]}
            />
          ))}
        </div>
      </section>
    );
  }

  const outboundSlice = selected.flight.slices[0];
  const returnSlice = selected.returns[0]?.slices[1];
  return (
    <section aria-labelledby="step-return" className="flex flex-col gap-3">
      {outboundSlice && (
        <div className="flex flex-col gap-2 rounded-lg border border-action-line bg-action-tint px-3.5 py-3 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <span className="field-label">Ida elegida</span>
            <button
              type="button"
              onClick={() => navigate({ search: (prev) => ({ ...prev, out: undefined }) })}
              className="text-[14px] font-semibold text-action hover:text-action-hover"
            >
              Cambiar ida
            </button>
          </div>
          <span className="flex items-center gap-2 text-[13px] text-muted">
            <AirlineBadge code={selected.flight.owner.code} />
            {selected.flight.owner.name} · <span className="data">{flightNumbersOf(selected.flight)}</span>
          </span>
          <SliceTimeline slice={outboundSlice} />
        </div>
      )}

      <StepHeading id="step-return" step={2} title="Elige tu vuelta">
        {returnSlice &&
          `${returnSlice.origin.city ?? returnSlice.origin.code} → ${returnSlice.destination.city ?? returnSlice.destination.code}`}
        {returnSlice?.segments[0] && ` · ${formatDate(returnSlice.segments[0].departing_at)}`}
      </StepHeading>
      <p className="text-[13px] text-muted" aria-live="polite">
        {selected.returns.length} {selected.returns.length === 1 ? "vuelta" : "vueltas"} para esta ida ·{" "}
        {priceNote}
      </p>
      <div className="flex flex-col gap-4 pt-1">
        {returnCards.map((flight) => (
          <FlightCard
            key={flight.key}
            flight={flight}
            insight={returnInsights.get(flight.key)}
            onSelect={onOpenFares}
            priceCaption="Ida y vuelta desde"
            sliceLabels={["Vuelta"]}
          />
        ))}
      </div>
    </section>
  );
}

function StepHeading({
  id,
  step,
  title,
  children,
}: {
  id: string;
  step: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <h2 id={id} className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[17px] font-bold">
      <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-ink font-mono text-[13px] font-semibold text-white">
        {step}
      </span>
      {title}
      <span className="text-[14px] font-normal text-ink-2">{children}</span>
    </h2>
  );
}
