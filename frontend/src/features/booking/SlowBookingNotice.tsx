import { Notice } from "@/components/ui/notice";
import { useNow } from "@/lib/useNow";
import { isTakingLong } from "./logic";

/**
 * Tells the traveler a booking is taking longer than usual and that the confirmation will reach
 * them by email, so they don't have to wait on the page. Shows nothing until the minute passes.
 */
export function SlowBookingNotice({ createdAt, className }: { createdAt: string; className?: string }) {
  const now = useNow(1000);
  if (!isTakingLong(createdAt, now)) return null;
  return (
    <Notice tone="warn" role="status" title="Está tardando más de lo habitual" className={className}>
      La aerolínea todavía no confirmó tu reserva. No hace falta que esperes acá: apenas se confirme te la
      enviamos por correo. El cobro solo se concreta cuando la aerolínea emite el ticket.
    </Notice>
  );
}
