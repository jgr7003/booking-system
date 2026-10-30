import type { Booking } from "@/api/client";
import { cn } from "@/lib/cn";
import { formatTotal } from "@/lib/format";
import { SlowBookingNotice } from "./SlowBookingNotice";
import { CARD } from "./styles";

const CONFIRMING_STEPS = [
  { label: "Recibimos tus datos y los del pago", state: "done" },
  { label: "Confirmando el lugar con la aerolínea", state: "current" },
  { label: "Cobrar y emitir el ticket", state: "next" },
] as const;

export function Confirming({ booking }: { booking?: Booking }) {
  return (
    <>
      <section role="status" aria-live="polite" className={`${CARD} overflow-hidden`}>
        <div className="flex items-center gap-3.5 border-b border-action-ring bg-action-soft px-6 py-4 max-sm:px-4">
          <span
            aria-hidden
            className="h-[30px] w-[30px] flex-none animate-spin rounded-full border-[3px] border-action-pale border-t-action"
          />
          <div className="flex flex-col gap-0.5">
            <h1 className="text-[18px] font-bold text-action-hover sm:text-[22px]">
              Estamos confirmando tu reserva con la aerolínea
            </h1>
            <span className="text-[14px] text-action-hover">
              Suele tardar menos de un minuto. Esta página se actualiza sola: no hace falta recargarla.
            </span>
          </div>
        </div>
        <div className="grid items-center gap-7 px-6 py-5 max-sm:px-4 sm:grid-cols-[minmax(0,1fr)_340px]">
          <ol className="flex flex-col gap-3 text-[15px]">
            {CONFIRMING_STEPS.map((step) => (
              <li
                key={step.label}
                aria-current={step.state === "current" ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2.5",
                  step.state === "current" && "font-semibold",
                  step.state === "next" && "text-muted",
                )}
              >
                {step.state === "done" ? (
                  <span
                    aria-hidden
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-ok text-[13px] font-bold text-white"
                  >
                    ✓
                  </span>
                ) : step.state === "current" ? (
                  <span
                    aria-hidden
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full border-2 border-action"
                  >
                    <span className="h-2.5 w-2.5 rounded-full bg-action" />
                  </span>
                ) : (
                  <span aria-hidden className="h-6 w-6 rounded-full border-2 border-line-dash" />
                )}
                {step.label}
              </li>
            ))}
          </ol>
          <div className="flex flex-col gap-1.5 rounded-lg border-2 border-dashed border-line-dash px-[18px] py-3.5">
            <span className="text-[12px] font-semibold tracking-[0.08em] text-muted uppercase">
              Código de reserva
            </span>
            <span
              aria-hidden
              className="font-mono text-[34px] font-semibold tracking-[0.14em] text-line-dash"
            >
              ······
            </span>
            <span className="text-[13px] text-muted">Aparece aquí cuando la aerolínea confirme.</span>
          </div>
        </div>
        {booking && (
          <SlowBookingNotice
            createdAt={booking.created_at}
            className="rounded-none border-x-0 border-b-0 border-t"
          />
        )}
        <div className="flex flex-wrap justify-between gap-2 border-t border-line-soft px-6 py-3 text-[14px] text-ink-2 max-sm:px-4">
          {booking && (
            <span>
              Total: <strong className="font-mono text-ink">{formatTotal(booking.price)}</strong>. Se cobra
              recién cuando la aerolínea confirma.
            </span>
          )}
          <span>Si cierras esta página, la reserva sigue. Vuelve con este mismo link.</span>
        </div>
      </section>
      <section aria-hidden className="flex flex-col gap-3">
        <span className="skeleton block h-[18px] w-40" />
        {[1, 0.6].map((opacity) => (
          <div key={opacity} style={{ opacity }} className={`${CARD} flex flex-col gap-3.5 px-5 py-4`}>
            <span className="skeleton block h-3.5 w-[260px] max-w-full" />
            <div className="grid grid-cols-[96px_minmax(0,1fr)_96px] items-center gap-[18px]">
              <span className="skeleton block h-[26px]" />
              <span className="block border-t-2 border-dashed border-line" />
              <span className="skeleton block h-[26px]" />
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
