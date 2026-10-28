import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/cn";
import { formatAmount, formatMoney, formatPassengers } from "@/lib/format";
import { totalsByCurrency } from "./logic";
import type { TripItem } from "./store";

/** "Resumen del viaje" (design). On mobile, the total and the button stick to the bottom. */
export function TripSummary({ items }: { items: TripItem[] }) {
  const first = items[0];
  const passengers = first
    ? formatPassengers(first.search.adults ?? 1, first.search.children?.length ?? 0)
    : "1 adulto";
  const totals = totalsByCurrency(items.map((i) => i.fare.price.total));
  // A trip is one flight for now: continuing books that flight.
  const continueButton = (label: string, className: string) =>
    first ? (
      <Link
        to="/checkout/$itemKey"
        params={{ itemKey: first.itemKey }}
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-action font-semibold text-white hover:bg-action-hover hover:text-white",
          className,
        )}
      >
        {label}
      </Link>
    ) : (
      <button
        type="button"
        disabled
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-line-soft font-semibold text-muted",
          className,
        )}
      >
        {label}
      </button>
    );

  return (
    <>
      <aside
        aria-labelledby="summary-title"
        className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-2.5 rounded-lg border border-line bg-white p-[18px] max-sm:max-w-none"
      >
        <h2 id="summary-title" className="text-[12px] font-semibold tracking-[0.06em] text-muted uppercase">
          Resumen del viaje
        </h2>
        {items.length === 0 && (
          <div className="flex justify-between text-[14px]">
            <span>Vuelos</span>
            <span>—</span>
          </div>
        )}
        {items.map((item) => {
          const slice = item.flight.slices[0];
          return (
            <div key={item.itemKey} className="flex justify-between gap-2 text-[14px]">
              <span>
                Vuelo {slice?.origin.code} → {slice?.destination.code}
                {item.flight.slices.length > 1 && (
                  <span className="block text-[12px] text-muted">Ida y vuelta</span>
                )}
              </span>
              <span className="data font-semibold">{formatAmount(item.fare.price.total)}</span>
            </div>
          );
        })}
        <div className="flex justify-between text-[14px] text-muted">
          <span>Hotel</span>
          <span>Sin agregar</span>
        </div>
        <div className="flex items-baseline justify-between border-t border-line-soft pt-2.5">
          <strong>Total · {passengers}</strong>
          <span className="data text-right text-[22px] font-semibold">
            {totals.length === 0
              ? "—"
              : totals.map((t) => (
                  <span key={t.currency} className="block">
                    {formatMoney(t)}
                  </span>
                ))}
          </span>
        </div>
        {continueButton("Continuar a pasajeros", "max-sm:hidden")}
        <p className="text-[12px] leading-normal text-muted">
          Cada vuelo es una oferta distinta de su aerolínea: tiene su propio vencimiento y se reserva como una
          orden separada. Si alguno cambia de precio al reconfirmar, se avisa antes de cobrar.
        </p>
      </aside>

      {items.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 flex items-center gap-3 border-t border-line bg-white px-3.5 pt-3 pb-5 sm:hidden">
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="text-[11px] text-muted">Total del viaje</span>
            <strong className="data text-[18px] whitespace-nowrap">
              {totals.map((t) => formatMoney(t)).join(" + ")}
            </strong>
          </span>
          {continueButton("Continuar", "px-[18px]")}
        </div>
      )}
    </>
  );
}
