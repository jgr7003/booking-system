import type { Booking } from "@/api/client";
import { AlertIcon } from "@/components/icons";
import { ProblemHeader } from "./ProblemHeader";
import { CARD } from "./styles";

/**
 * "Error de emisión": the airline may have issued the booking, but it could not be confirmed or
 * charged. There is no design board for it yet; it follows the "no se pudo reservar" one in amber.
 * It never offers to try again: rebooking the same flight could duplicate an order.
 */
export function IssuanceError({ booking }: { booking: Booking }) {
  return (
    <section role="alert" className={`${CARD} overflow-hidden`}>
      <ProblemHeader
        tone="warn"
        title="Error de emisión"
        subtitle="Tu reserva quedó en revisión."
        icon={<AlertIcon width={18} height={18} />}
      />
      <div className="flex max-w-[760px] flex-col gap-3 px-6 py-5 text-[16px] leading-normal text-ink-2 max-sm:px-4">
        <p>
          Tuvimos un problema al emitir tu reserva con la aerolínea y no pudimos confirmarla ni descartarla de
          forma automática. <strong className="text-ink">No vuelvas a reservar este vuelo</strong>: podríamos
          duplicar la reserva.
        </p>
        <p>
          Necesita una revisión manual. Mientras tanto no se concretó ningún cobro, aunque el monto puede
          aparecer retenido en tu tarjeta hasta que se resuelva.
        </p>
        <p className="text-[14px]">
          Si necesitás ayuda, indicá este número de reserva:{" "}
          <code className="font-mono font-semibold text-ink">{booking.id}</code>
        </p>
      </div>
    </section>
  );
}
