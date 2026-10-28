import type { Money } from "@/api/client";
import { Dialog } from "@/components/ui/dialog";
import { formatTotal } from "@/lib/format";

/**
 * The airline changed the price when it was reconfirmed (design board "Estados"). Nothing is
 * charged until the traveler accepts: there is no way to close it without choosing.
 */
export function PriceChangedDialog({
  open,
  fareName,
  before,
  now,
  busy,
  onAccept,
  onReject,
}: {
  open: boolean;
  fareName: string;
  before: Money;
  now: Money;
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
}) {
  const difference = Number(now.amount) - Number(before.amount);
  return (
    <Dialog open={open} title={`La aerolínea actualizó el precio de ${fareName}`}>
      <div className="grid grid-cols-2 gap-2.5 text-[14px]">
        <div className="rounded-md bg-canvas p-2.5">
          <span className="block text-[12px] text-muted">Antes</span>
          <span className="font-mono font-semibold line-through">{formatTotal(before)}</span>
        </div>
        <div className="rounded-md bg-warn-soft p-2.5">
          <span className="block text-[12px] text-warn">Ahora</span>
          <span className="font-mono font-semibold">{formatTotal(now)}</span>
        </div>
      </div>
      <p className="text-[13px] text-ink-2">
        {difference > 0 ? "Subió" : "Bajó"}{" "}
        <span className="font-mono">
          {formatTotal({ amount: Math.abs(difference).toFixed(2), currency: now.currency })}
        </span>
        . No se cobra nada hasta que lo aceptes.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onAccept}
          disabled={busy}
          className="h-11 rounded-md bg-action px-4 font-semibold text-white disabled:opacity-70"
        >
          Aceptar y continuar
        </button>
        <button
          type="button"
          onClick={onReject}
          disabled={busy}
          className="h-11 rounded-md border border-line bg-white px-4 disabled:opacity-70"
        >
          Cancelar
        </button>
      </div>
    </Dialog>
  );
}
