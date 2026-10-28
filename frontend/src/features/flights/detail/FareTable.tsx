import type { Fare, Flight } from "@/api/client";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import { bagCell, conditionCell, fareCarryOn, fareCheckedBags, fareName } from "@/lib/flights/fares";
import { formatAmount } from "@/lib/format";
import { penaltyCell } from "./logic";
import { SECTION, SECTION_TITLE } from "./styles";

const FARE_GRID = "grid grid-cols-[40px_minmax(0,1.4fr)_110px_repeat(4,minmax(0,1fr))] items-center";

export function FareTable({
  flight,
  selected,
  onSelect,
}: {
  flight: Flight;
  selected: Fare;
  onSelect: (fare: Fare) => void;
}) {
  return (
    <section aria-labelledby="fares" className={SECTION}>
      <h2 id="fares" className={SECTION_TITLE}>
        Tarifa{" "}
        <span className="text-[13px] font-normal text-muted">
          · {flight.fares.length === 1 ? "1 opción" : `${flight.fares.length} opciones para este mismo vuelo`}
        </span>
      </h2>
      {/* Mobile (design): one radio row per fare with a short summary. */}
      <fieldset className="text-[13px] sm:hidden">
        <legend className="sr-only">Tarifa</legend>
        {flight.fares.map((fare, i) => {
          const checked = bagCell(fareCheckedBags(fare), "checked");
          const carryOn = bagCell(fareCarryOn(fare), "carry_on");
          const change = conditionCell(fare.conditions.change);
          return (
            <label
              key={fare.offer_id}
              className={cn(
                "flex cursor-pointer items-center gap-2.5 px-3 py-2.5",
                i > 0 && "border-t border-line-soft",
                fare.offer_id === selected.offer_id && "bg-action-soft",
              )}
            >
              <input
                type="radio"
                name="fare-mobile"
                checked={fare.offer_id === selected.offer_id}
                onChange={() => onSelect(fare)}
                className="h-[18px] w-[18px] accent-action"
              />
              <span className="flex-1">
                <strong>{fareName(fare)}</strong>
                <span className="block text-muted">
                  Valija {checked.label.toLowerCase()} · mano {carryOn.label.toLowerCase()} · cambio{" "}
                  {change.label.toLowerCase()}
                </span>
              </span>
              <span className="data font-semibold">{formatAmount(fare.price.total)}</span>
            </label>
          );
        })}
      </fieldset>
      <div className="overflow-x-auto max-sm:hidden">
        <fieldset className="min-w-[720px]">
          <legend className="sr-only">Tarifa</legend>
          <div aria-hidden className={cn(FARE_GRID, "field-label border-b border-line-soft bg-surface-2")}>
            <span />
            <span className="px-2 py-2.5">Tarifa</span>
            <span className="px-2 py-2.5 text-right">Total</span>
            <span className="px-2 py-2.5">Valija</span>
            <span className="px-2 py-2.5">Mano</span>
            <span className="px-2 py-2.5">Cambio</span>
            <span className="px-2 py-2.5">Reembolso</span>
          </div>
          {flight.fares.map((fare) => {
            const on = fare.offer_id === selected.offer_id;
            const cells = [
              bagCell(fareCheckedBags(fare), "checked"),
              bagCell(fareCarryOn(fare), "carry_on"),
              penaltyCell(fare.conditions.change),
              penaltyCell(fare.conditions.refund),
            ];
            return (
              <label
                key={fare.offer_id}
                className={cn(
                  FARE_GRID,
                  "w-full cursor-pointer border-b border-line-soft text-left text-[14px] has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-action",
                  on ? "bg-action-soft shadow-[inset_3px_0_0_#1D4ED8]" : "bg-white hover:bg-surface-2",
                )}
              >
                <input
                  type="radio"
                  name="fare"
                  checked={on}
                  onChange={() => onSelect(fare)}
                  className="sr-only"
                />
                <span aria-hidden className="flex justify-center">
                  <span
                    className={cn(
                      "box-border h-4 w-4 rounded-full",
                      on ? "border-[5px] border-action" : "border-2 border-subtle",
                    )}
                  />
                </span>
                <span className="px-2 py-3 font-semibold">{fareName(fare)}</span>
                <span className="data px-2 py-3 text-right font-semibold">
                  {formatAmount(fare.price.total)}
                </span>
                {cells.map((cell, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: fixed columns.
                  <span key={i} className={cn("px-2 py-3", toneTextClass(cell.tone))}>
                    {cell.label}
                  </span>
                ))}
              </label>
            );
          })}
        </fieldset>
      </div>
    </section>
  );
}
