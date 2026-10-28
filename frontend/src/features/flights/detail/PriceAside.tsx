import { Link } from "@tanstack/react-router";
import type { Fare, Flight } from "@/api/client";
import { cn } from "@/lib/cn";
import { fareName } from "@/lib/flights/fares";
import { type DetailSearch, pickSearch } from "@/lib/flights/search";
import { formatAmount, formatRemaining, utcDateTime, utcTime } from "@/lib/format";
import { useExpiry } from "@/lib/useExpiry";

export function PriceAside({
  flight,
  fare,
  search,
  onSave,
}: {
  flight: Flight;
  fare: Fare;
  search: DetailSearch;
  onSave: () => void;
}) {
  const { expired } = useExpiry(fare.expires_at);
  const { base, taxes, total } = fare.price;
  const passengers = (search.adults ?? 1) + (search.children?.length ?? 0);
  const basePct = base && taxes ? Math.round((Number(base.amount) / Number(total.amount)) * 100) : null;
  const saveButton = (className: string, short = false) =>
    expired ? (
      <Link
        to="/flights"
        search={{ ...pickSearch(search), hl: flight.key }}
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-action px-4 font-semibold text-white hover:text-white",
          className,
        )}
      >
        {short ? "Actualizar precios" : "La oferta venció · actualizar precios"}
      </Link>
    ) : (
      <button
        type="button"
        onClick={onSave}
        className={cn(
          "flex h-12 shrink-0 items-center justify-center rounded-md bg-action px-4 font-semibold text-white hover:bg-action-hover",
          className,
        )}
      >
        {short ? "Guardar en mi viaje" : `Guardar ${fareName(fare)} en mi viaje`}
      </button>
    );

  return (
    <>
      <aside
        aria-label="Resumen del precio"
        className="flex max-w-[360px] flex-[1_1_300px] flex-col gap-3 max-sm:max-w-none"
      >
        <div className="flex flex-col gap-3 rounded-lg border border-line bg-white p-[18px]">
          <span className="text-[12px] font-semibold tracking-[0.06em] text-muted uppercase">
            Precio · {passengers === 1 ? "1 adulto" : `${passengers} pasajeros`}
          </span>
          <div className="flex justify-between text-[14px]">
            <span>Tarifa base</span>
            <span className="data">{base ? formatAmount(base) : "Sin dato"}</span>
          </div>
          <div className="flex justify-between text-[14px]">
            <span>Impuestos y cargos</span>
            <span className="data">{taxes ? formatAmount(taxes) : "Sin dato"}</span>
          </div>
          {basePct !== null && (
            <>
              <div aria-hidden className="flex h-2 overflow-hidden rounded bg-line">
                <span className="bg-action" style={{ width: `${basePct}%` }} />
              </div>
              <p className="text-[12px] text-muted">
                La tarifa base es el {basePct} % del total; el resto son impuestos y cargos de aeropuerto.
              </p>
            </>
          )}
          <div className="flex items-baseline justify-between border-t border-line-soft pt-3">
            <span className="font-semibold">Total</span>
            <span className="data text-[24px] font-semibold">
              {formatAmount(total)} <span className="text-[13px]">{total.currency}</span>
            </span>
          </div>
          <div className="flex justify-between text-[13px] text-ink-2">
            <span>CO₂ estimado</span>
            <span className="data">
              {flight.emissions_kg !== null ? `${flight.emissions_kg} kg` : "Sin dato"}
            </span>
          </div>
          {saveButton("max-sm:hidden")}
        </div>
        {fare.payment.can_hold && fare.payment.payment_required_by && (
          <div className="flex flex-col gap-1.5 rounded-lg border border-line bg-white px-4 py-3.5 text-[13px] leading-normal">
            <strong className="text-[14px]">Reservá ahora, pagá después</strong>
            <span>
              Esta tarifa se puede reservar sin pagar y pagar hasta el{" "}
              <strong className="font-mono">{utcDateTime(fare.payment.payment_required_by)}</strong>. La
              elección se hace en el paso de pago.
            </span>
          </div>
        )}
        <div className="rounded-lg border border-warn-line bg-warn-soft px-4 py-3.5 text-[13px] leading-normal text-warn-ink">
          <strong className="block text-[14px]">
            {expired ? "La oferta venció" : `La oferta vence a las ${utcTime(fare.expires_at)} UTC`}
          </strong>
          Antes de reservar se vuelve a confirmar el precio con la aerolínea. Si cambió, se avisa antes de
          cobrar.
        </div>
      </aside>

      <div className="fixed inset-x-0 bottom-0 z-20 flex items-center gap-3 border-t border-line bg-white px-3.5 pt-3 pb-5 sm:hidden">
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="data text-[18px] font-semibold whitespace-nowrap">
            {formatAmount(total)} {total.currency}
          </span>
          <MobileExpiry expiresAt={fare.expires_at} />
        </span>
        {saveButton("text-[15px]", true)}
      </div>
    </>
  );
}

function MobileExpiry({ expiresAt }: { expiresAt: string }) {
  const { remaining, expired, warning } = useExpiry(expiresAt);
  return (
    <span className={cn("text-[11px] font-semibold", warning ? "text-warn" : "text-muted")}>
      {expired ? "Oferta vencida" : `Vence en ${formatRemaining(remaining)}`}
    </span>
  );
}
