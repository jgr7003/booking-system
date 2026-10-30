import { useState } from "react";
import type { Fare } from "@/api/client";
import { ToneCell } from "@/components/ui/tone";
import { bagCell, conditionCell, fareCarryOn, fareCheckedBags, fareName } from "@/lib/flights/fares";
import { formatAmount, formatMoney } from "@/lib/format";

interface FareMatrixProps {
  fares: Fare[];
  onChoose: (fare: Fare) => void;
}

/** Fares of a flight side by side (design): total, bags, change and refund, then "Elegir". */
export function FareMatrix({ fares, onChoose }: FareMatrixProps) {
  const [chosen, setChosen] = useState<string | null>(null);
  const currency = fares[0]?.price.total.currency ?? "";
  const rows = [
    { label: "Maleta de bodega", cell: (f: Fare) => bagCell(fareCheckedBags(f), "checked") },
    { label: "Equipaje de mano", cell: (f: Fare) => bagCell(fareCarryOn(f), "carry_on") },
    { label: "Cambio", cell: (f: Fare) => conditionCell(f.conditions.change) },
    { label: "Reembolso", cell: (f: Fare) => conditionCell(f.conditions.refund) },
  ];

  return (
    <table
      className="w-full table-fixed border-separate border-spacing-1.5 text-[13px]"
      style={{ minWidth: 160 + fares.length * 126 }}
    >
      <caption className="sr-only">Tarifas disponibles para este vuelo</caption>
      <colgroup>
        <col className="w-40" />
      </colgroup>
      <thead>
        <tr>
          <td />
          {fares.map((fare) => (
            <th key={fare.offer_id} scope="col" className="py-1 text-left font-semibold">
              {fareName(fare)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row" className="py-1.5 text-left font-normal text-ink-2">
            Total {currency}
          </th>
          {fares.map((fare) => (
            <td key={fare.offer_id}>
              <span className="data block rounded bg-white px-2 py-1.5 font-semibold">
                {formatAmount(fare.price.total)}
              </span>
            </td>
          ))}
        </tr>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row" className="py-1.5 text-left font-normal text-ink-2">
              {row.label}
            </th>
            {fares.map((fare) => (
              <td key={fare.offer_id}>
                <ToneCell cell={row.cell(fare)} className="flex w-full" />
              </td>
            ))}
          </tr>
        ))}
        <tr>
          <td />
          {fares.map((fare) => (
            <td key={fare.offer_id}>
              <button
                type="button"
                disabled={chosen !== null}
                aria-label={`Elegir ${fareName(fare)} por ${formatMoney(fare.price.total)}`}
                onClick={() => {
                  setChosen(fare.offer_id);
                  onChoose(fare);
                }}
                className="flex h-10 w-full items-center justify-center rounded-md bg-action font-semibold text-white hover:bg-action-hover disabled:opacity-70"
              >
                Elegir
              </button>
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}
