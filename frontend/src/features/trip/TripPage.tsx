import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import { HotelIcon, LogoIcon } from "@/components/icons";
import { StepCircles, StepCount } from "@/components/layout/Steps";
import { TopBar } from "@/components/layout/TopBar";
import { formatShortDate } from "@/lib/format";
import { searchedCity } from "@/lib/placeLabels";
import { type TripItem, tripItems, useTrip } from "./store";
import { TripItemCard } from "./TripItemCard";
import { TripSummary } from "./TripSummary";

/** Design board "Tu viaje". */
export function TripPage() {
  // Raw state with a shallow comparison; deriving the list inside the selector would loop renders.
  const state = useTrip(useShallow((s) => ({ items: s.items, order: s.order })));
  const items = useMemo(() => tripItems(state), [state]);
  const restore = useTrip((s) => s.restore);
  const [removed, setRemoved] = useState<{ item: TripItem; index: number } | null>(null);
  const last = items.at(-1);
  // The searched destination, not the airport the flight lands at (NYC, not EWR).
  const destination = last ? searchedCity(last.search.to, last.flight.slices[0]?.destination) : null;
  const title = destination ? `Tu viaje a ${destination}` : "Tu viaje está vacío";

  return (
    <>
      <TopBar>
        <span className="flex-1" />
        <span className="max-sm:hidden">
          <StepCircles current={1} canOpenTrip />
        </span>
        <span className="sm:hidden">
          <StepCount current={1} />
        </span>
      </TopBar>

      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-5 px-3 pt-3.5 pb-28 sm:px-5 sm:pt-6 sm:pb-14">
        <section aria-labelledby="trip-title" className="flex min-w-0 flex-[999_1_640px] flex-col gap-3.5">
          <div className="flex flex-col gap-1">
            <h1 id="trip-title" className="text-[22px] font-bold sm:text-[28px]">
              {title}
            </h1>
            <p className="text-[15px] text-ink-2">
              {items.length
                ? "Revisa tu vuelo y sigue con los datos del pasajero."
                : "Busca un vuelo para empezar."}
            </p>
          </div>

          {items.map((item, i) => (
            <TripItemCard
              key={item.itemKey}
              item={item}
              position={i + 1}
              onRemoved={(result) => setRemoved(result)}
            />
          ))}

          {removed && (
            <div
              role="status"
              className="flex items-center justify-between gap-3 rounded-lg bg-ink px-4 py-2.5 text-[14px] text-white"
            >
              <span>
                Quitaste el vuelo {removed.item.flight.slices[0]?.origin.code} →{" "}
                {removed.item.flight.slices[0]?.destination.code} del{" "}
                {formatShortDate(removed.item.search.depart)}.
              </span>
              <button
                type="button"
                onClick={() => {
                  restore(removed.item, removed.index);
                  setRemoved(null);
                }}
                className="h-[38px] rounded-md border border-muted-2 px-3.5 font-semibold"
              >
                Deshacer
              </button>
            </div>
          )}

          <div className="grid gap-2.5 sm:grid-cols-2">
            {/* For now a trip is a single flight for one traveler: more flights and hotels come later. */}
            {items.length ? (
              <button type="button" disabled title="Próximamente" className={COMING_SOON}>
                <LogoIcon width={18} height={18} />
                Agregar otro vuelo · próximamente
              </button>
            ) : (
              <Link
                to="/"
                className="inline-flex h-[52px] items-center justify-center gap-2 rounded-lg border border-dashed border-action bg-white text-[15px] font-semibold text-action sm:h-14"
              >
                <LogoIcon width={18} height={18} />
                Buscar vuelo
              </Link>
            )}
            <button type="button" disabled title="Próximamente" className={COMING_SOON}>
              <HotelIcon />
              Agregar hotel · próximamente
            </button>
          </div>
        </section>

        <TripSummary items={items} />
      </main>
    </>
  );
}

const COMING_SOON =
  "inline-flex h-[52px] items-center justify-center gap-2 rounded-lg border border-dashed border-line-dash bg-white text-[15px] font-semibold text-subtle sm:h-14";
