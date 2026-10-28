import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Fare, Flight, SearchResponse } from "@/api/client";
import { flightKeys, useFlightSearch } from "@/api/flights";
import { CalendarIcon, DepartureIcon, PencilIcon, PersonIcon, SwapIcon } from "@/components/icons";
import { StepCircles } from "@/components/layout/Steps";
import { BarDivider, ProgressBar, TopBar } from "@/components/layout/TopBar";
import { useAddToTrip, useTrip } from "@/features/trip/public";
import { flightNumbersOf } from "@/lib/flights/itinerary";
import {
  CABIN_LABELS,
  type CompleteSearch,
  isComplete,
  pickSearch,
  type ResultsSearch,
  toCriteria,
} from "@/lib/flights/search";
import { formatDate, formatPassengers, formatShortDate, formatTime } from "@/lib/format";
import { searchedCity } from "@/lib/placeLabels";
import { FaresDialog } from "./FaresDialog";
import { FilterChips, SortSelect } from "./FiltersBar";
import { FlightCard } from "./FlightCard";
import {
  activeFilterCount,
  airlinesOf,
  applyFilters,
  filtersFromSearch,
  flightInsights,
  isRoundTrip,
  outboundKeyOf,
  relaxSuggestions,
  sortFlights,
} from "./logic";
import {
  ExpiredDialog,
  ExpiryBadge,
  NoFlightsState,
  NoMatchesState,
  SearchErrorState,
  SearchingState,
} from "./ResultStates";
import { RoundTripSteps } from "./RoundTripSteps";

/** Design boards "Espera" and "Resultados". */
export function ResultsPage() {
  const search = useSearch({ from: "/flights" });
  const complete = isComplete(search) ? search : null;
  // Stable criteria: only the search fields matter, not the view state (sort, filters).
  const criteriaKey = JSON.stringify(complete ? pickSearch(complete) : null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: recomputed only when the criteria change.
  const criteria = useMemo(() => (complete ? toCriteria(complete) : null), [criteriaKey]);
  const query = useFlightSearch(criteria);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  if (!complete || !criteria) {
    return (
      <>
        <TopBar />
        <main className="mx-auto flex max-w-[1240px] flex-col items-start gap-3 px-4 py-6 sm:px-5">
          <h1 className="text-[22px] font-bold">Falta completar la búsqueda</h1>
          <Link to="/" search={pickSearch(search)} className="font-semibold">
            Buscar vuelos
          </Link>
        </main>
      </>
    );
  }

  return (
    <>
      <ResultsBar search={complete} searching={query.isPending} />
      {query.isPending && <ProgressBar label="Buscando ofertas" />}
      <main className="mx-auto flex max-w-[1240px] flex-col gap-4 px-3 pt-3.5 pb-14 sm:px-5 sm:pt-6">
        {query.isPending ? (
          <>
            <ResultsTitle search={complete} />
            <SearchingState
              onCancel={() => {
                queryClient.cancelQueries({ queryKey: flightKeys.search(criteria) });
                navigate({ to: "/", search: pickSearch(complete) });
              }}
            />
          </>
        ) : query.isError ? (
          <SearchErrorState error={query.error} onRetry={() => query.refetch()} search={complete} />
        ) : (
          <Results
            data={query.data}
            search={search}
            complete={complete}
            onRefresh={() => query.refetch()}
            refreshing={query.isFetching}
          />
        )}
      </main>
    </>
  );
}

/** Dark bar of the results: search summary, "Modificar" and steps (design). */
function ResultsBar({ search, searching }: { search: CompleteSearch; searching: boolean }) {
  const tripCount = useTrip((s) => s.order.length);
  const passengers = formatPassengers(search.adults ?? 1, search.children?.length ?? 0);
  const cabin = CABIN_LABELS[search.cabin ?? "economy"];
  const route = (
    <span className="data inline-flex items-center gap-1.5 font-semibold text-white">
      {search.from} {search.ret ? <SwapIcon /> : "→"} {search.to}
    </span>
  );
  const modify = (
    <Link
      to="/"
      search={pickSearch(search)}
      className="inline-flex items-center gap-1.5 font-semibold text-action-light hover:text-white"
    >
      <PencilIcon />
      Modificar
    </Link>
  );

  return (
    <TopBar className="max-sm:gap-y-1">
      {/* Desktop: summary in items separated by dividers. */}
      <div className="flex flex-1 flex-wrap items-center gap-y-1.5 text-[14px] text-line-soft max-sm:hidden">
        <span className="px-3">{route}</span>
        <BarDivider />
        <span className="inline-flex items-center gap-1.5 px-3">
          <CalendarIcon />
          {formatShortDate(search.depart)}
          {search.ret && ` – ${formatShortDate(search.ret)}`}
        </span>
        <BarDivider />
        <span className="inline-flex items-center gap-1.5 px-3">
          <PersonIcon />
          {passengers} · {cabin}
          {search.direct && " · Solo directos"}
        </span>
        {!searching && (
          <>
            <BarDivider />
            <span className="px-3">{modify}</span>
          </>
        )}
      </div>
      {!searching && (
        <span className="max-sm:hidden">
          <StepCircles current={0} canOpenTrip={tripCount > 0} />
        </span>
      )}
      {/* Mobile: one line with the summary and "Modificar". */}
      <div className="flex w-full items-center justify-between gap-2 text-[13px] sm:hidden">
        <span className="data text-[14px] font-semibold">
          {search.from} {search.ret ? "⇄" : "→"} {search.to} · {formatShortDate(search.depart)} ·{" "}
          {search.adults ?? 1} ad.
        </span>
        {modify}
      </div>
    </TopBar>
  );
}

function ResultsTitle({ search, data }: { search: CompleteSearch; data?: SearchResponse }) {
  const first = data?.flights[0]?.slices[0];
  // The searched places, not the first result's airports (a search to NYC may land at EWR).
  const origin = searchedCity(search.from, first?.origin);
  const destination = searchedCity(search.to, first?.destination);
  return (
    <h1 className="flex flex-wrap items-center gap-2.5 text-[16px] font-bold sm:text-[22px]">
      <DepartureIcon className="max-sm:hidden" />
      {search.ret ? "Ida y vuelta" : "Ida"}: {origin} a {destination}
      <span aria-hidden className="h-5 w-px bg-subtle max-sm:hidden" />
      <span className="text-[13px] font-normal text-ink-2 sm:text-[16px]">
        {formatDate(search.depart, { longWeekday: true })}
      </span>
    </h1>
  );
}

interface ResultsProps {
  data: SearchResponse;
  search: ResultsSearch;
  complete: CompleteSearch;
  onRefresh: () => void;
  refreshing: boolean;
}

function Results({ data, search, complete, onRefresh, refreshing }: ResultsProps) {
  const addToTrip = useAddToTrip();
  const navigate = useNavigate({ from: "/flights" });
  const filters = useMemo(() => filtersFromSearch(search), [search]);
  const flights = useMemo(
    () => sortFlights(applyFilters(data.flights, filters), search.sort),
    [data.flights, filters, search.sort],
  );
  // Flight whose fares are open in the modal, and the last one opened (kept when the modal closes).
  const [openKey, setOpenKey] = useState<string | null>(search.hl ?? null);
  const [watchedKey, setWatchedKey] = useState<string | null>(search.hl ?? null);
  // Tags and notes depend on the whole list: computed once per list, not per card.
  const insights = useMemo(() => flightInsights(flights), [flights]);
  const searchId = data.search_id;
  const openFares = useCallback((key: string) => {
    setOpenKey(key);
    setWatchedKey(key);
  }, []);
  const choose = useCallback(
    (flight: Flight, fare: Fare) => addToTrip(flight, fare, complete, searchId),
    [addToTrip, complete, searchId],
  );
  const cardSearch = useMemo(() => pickSearch(complete), [complete]);
  // Decided on the whole response, so applying a filter never switches between the two views.
  const roundTrip = useMemo(() => isRoundTrip(data.flights), [data.flights]);

  // A highlighted flight (coming back from "Tu viaje" or after refreshing prices) opens and scrolls into view.
  // In two steps, the outbound of the highlighted combination is selected first.
  useEffect(() => {
    if (!search.hl) return;
    setOpenKey(search.hl);
    setWatchedKey(search.hl);
    const combination = roundTrip ? data.flights.find((f) => f.key === search.hl) : undefined;
    const out = combination ? outboundKeyOf(combination) : undefined;
    if (out && out !== search.out) navigate({ search: (prev) => ({ ...prev, out }), replace: true });
    document.getElementById(`flight-${search.hl}`)?.scrollIntoView({ block: "center" });
  }, [search.hl, search.out, roundTrip, data.flights, navigate]);

  const passengers = formatPassengers(complete.adults ?? 1, complete.children?.length ?? 0);
  const currency = data.flights[0]?.lowest_price.currency;
  const watched = data.flights.find((f) => f.key === watchedKey);
  const watchedLabel = watched
    ? `${flightNumbersOf(watched)}, ${formatTime(watched.slices[0]?.segments[0]?.departing_at ?? "")}`
    : null;

  if (data.flights.length === 0) {
    return (
      <>
        <ResultsTitle search={complete} />
        <NoFlightsState search={search} />
      </>
    );
  }

  return (
    <section className="flex flex-col gap-4" aria-busy={refreshing}>
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <ResultsTitle search={complete} data={data} />
        <SortSelect search={search} />
      </div>

      <div className="flex flex-wrap items-center gap-2 max-sm:-mx-3 max-sm:flex-nowrap max-sm:overflow-x-auto max-sm:px-3">
        <span className="shrink-0 text-[14px] max-sm:hidden">Filtrar por:</span>
        <FilterChips search={search} airlines={airlinesOf(data.flights)} />
        {data.expires_at && (
          <span className="ml-auto max-sm:hidden">
            <ExpiryBadge expiresAt={data.expires_at} />
          </span>
        )}
      </div>

      {!(roundTrip && flights.length > 0) && (
        <p className="text-[13px] text-muted" aria-live="polite">
          {flights.length} {flights.length === 1 ? "vuelo" : "vuelos"} · precio total por {passengers}, con
          impuestos
          {currency ? `, en ${currency}` : ""}
        </p>
      )}

      {flights.length === 0 ? (
        <NoMatchesState
          suggestions={relaxSuggestions(data.flights, filters)}
          activeCount={activeFilterCount(filters)}
          total={data.flights.length}
        />
      ) : roundTrip ? (
        <RoundTripSteps
          flights={flights}
          selectedOutbound={search.out}
          passengers={passengers}
          currency={currency}
          sort={search.sort}
          onOpenFares={openFares}
        />
      ) : (
        <div className="flex flex-col gap-4 pt-1">
          {flights.map((flight) => (
            <FlightCard
              key={flight.key}
              flight={flight}
              insight={insights.get(flight.key)}
              onSelect={openFares}
            />
          ))}
        </div>
      )}

      <FaresDialog
        flight={openKey ? flights.find((f) => f.key === openKey) : undefined}
        insight={openKey ? insights.get(openKey) : undefined}
        search={cardSearch}
        onChoose={choose}
        onClose={() => setOpenKey(null)}
      />

      {data.expires_at && (
        <ExpiredDialog
          expiresAt={data.expires_at}
          watching={watchedLabel}
          refreshing={refreshing}
          search={complete}
          onRefresh={() => {
            if (watchedKey) navigate({ search: (prev) => ({ ...prev, hl: watchedKey }), replace: true });
            onRefresh();
          }}
        />
      )}
    </section>
  );
}
