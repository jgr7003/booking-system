import type { OrderSlice } from "@/api/client";
import { toneTextClass } from "@/components/ui/tone";
import { cn } from "@/lib/cn";
import { fareNames, type Item, includedItems, isRoundTrip, type Order, sameIncluded } from "./logic";
import { CARD } from "./styles";

export function Included({ order, reference }: { order: Order; reference: string }) {
  const same = sameIncluded(order);
  const groups = same
    ? [{ label: "", items: includedItems(order.slices[0] as OrderSlice, order) }]
    : order.slices.map((slice, i) => ({
        label: i === 0 ? "Ida" : "Vuelta",
        items: includedItems(slice, order),
      }));
  // Nothing reported about bags and conditions: say where to find them (design: state 3).
  const unknown = groups.every((g) => g.items.slice(0, 4).every((item) => item.tone === "na"));
  const url = order.owner.conditions_of_carriage_url;

  return (
    <section
      aria-labelledby="included"
      className={`${CARD} flex flex-col gap-3 px-5 py-[18px] max-sm:gap-2.5 max-sm:p-3.5`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-1.5">
        <h2 id="included" className="text-[16px] font-bold sm:text-[18px]">
          Qué incluye tu tarifa {fareNames(order)}
        </h2>
        {isRoundTrip(order) && same && (
          <span className="text-[13px] text-muted max-sm:hidden">Igual en la ida y en la vuelta</span>
        )}
      </div>
      {groups.map((group) => (
        <div key={group.label || "all"} className="flex flex-col gap-2">
          {group.label && <strong className="text-[14px]">{group.label}</strong>}
          <IncludedList items={group.items} />
        </div>
      ))}
      {unknown && (
        <p className="text-[13px] text-muted">
          {order.owner.name} no informó estos datos. Consultalos en sus condiciones de transporte o con la
          aerolínea, usando tu código {reference}.
        </p>
      )}
      {url && (
        <p className="text-[13px] text-muted">
          <span className="max-sm:hidden">Las reglas completas están en las </span>
          <a href={url} target="_blank" rel="noreferrer">
            <span className="sm:hidden">Condiciones</span>
            <span className="max-sm:hidden">condiciones</span> de transporte de {order.owner.name}
          </a>
          <span className="max-sm:hidden">.</span>
        </p>
      )}
    </section>
  );
}

function IncludedList({ items }: { items: Item[] }) {
  return (
    <ul className="grid grid-cols-3 gap-2 max-sm:flex max-sm:flex-col max-sm:gap-0">
      {items.map((item) => (
        <li
          key={item.label}
          className="flex flex-col gap-1.5 rounded-md border border-line-soft px-3 py-2.5 max-sm:flex-row max-sm:justify-between max-sm:gap-2.5 max-sm:rounded-none max-sm:border-0 max-sm:border-t max-sm:px-0 max-sm:py-[9px]"
        >
          <span className="text-[13px] text-ink-2 max-sm:text-[14px]">{item.label}</span>
          <span className={cn("text-[15px] font-semibold max-sm:text-[14px]", toneTextClass(item.tone))}>
            {item.value}
          </span>
        </li>
      ))}
    </ul>
  );
}
