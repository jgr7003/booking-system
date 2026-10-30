import type { Fare, Flight } from "@/api/client";
import { toneTextClass } from "@/components/ui/tone";
import type { Cell } from "@/lib/cell";
import { bagCell, fareCarryOn, fareCheckedBags, fareName } from "@/lib/flights/fares";
import { isZero } from "@/lib/format";
import { benefitCell, penaltyCell } from "./logic";

export function FareConditions({ flight, fare }: { flight: Flight; fare: Fare }) {
  const benefits = fare.slices[0]?.benefits;
  const penalties = [fare.conditions.change.penalty, fare.conditions.refund.penalty].filter(
    (p): p is NonNullable<typeof p> => Boolean(p) && !isZero(p as NonNullable<typeof p>),
  );
  const penaltyCurrency = penalties[0]?.currency;
  const priceCurrency = fare.price.total.currency;
  const conditions: { k: string; cell: Cell }[] = [
    { k: "Cambio antes de la salida", cell: penaltyCell(fare.conditions.change) },
    { k: "Reembolso antes de la salida", cell: penaltyCell(fare.conditions.refund) },
    { k: "Maleta de bodega", cell: bagCell(fareCheckedBags(fare), "checked") },
    { k: "Equipaje de mano", cell: bagCell(fareCarryOn(fare), "carry_on") },
    { k: "Selección de asiento anticipada", cell: benefitCell(benefits?.advance_seat_selection, "Incluida") },
    { k: "Embarque prioritario", cell: benefitCell(benefits?.priority_boarding, "Incluido") },
    { k: "Check-in prioritario", cell: benefitCell(benefits?.priority_check_in, "Incluido") },
  ];

  return (
    <section
      aria-labelledby="conditions"
      className="flex flex-col gap-3 rounded-lg border border-line bg-white px-[18px] py-4"
    >
      <h2 id="conditions" className="text-[16px] font-semibold">
        Condiciones de {fareName(fare)}
      </h2>
      <div className="grid gap-2.5 text-[14px] sm:[grid-template-columns:repeat(auto-fit,minmax(220px,1fr))]">
        {conditions.map(({ k, cell }) => (
          <div key={k} className="flex flex-col gap-1 rounded-md border border-line-soft px-3 py-2.5">
            <span className="text-[12px] text-muted">{k}</span>
            <span className={toneTextClass(cell.tone)}>{cell.label}</span>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-muted">
        {penaltyCurrency && penaltyCurrency !== priceCurrency
          ? `Las penalidades las informa la aerolínea en ${penaltyCurrency}; el precio está en ${priceCurrency}. Se muestran en su moneda original, sin convertir. `
          : "«Sin dato»: la aerolínea no lo informa para esta tarifa. "}
        {flight.owner.conditions_of_carriage_url && (
          <>
            Ver{" "}
            <a href={flight.owner.conditions_of_carriage_url} target="_blank" rel="noreferrer">
              condiciones de transporte de {flight.owner.name}
            </a>
            .
          </>
        )}
      </p>
    </section>
  );
}
