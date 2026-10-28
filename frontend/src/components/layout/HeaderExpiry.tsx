import { ClockIcon } from "@/components/icons";
import { cn } from "@/lib/cn";
import { formatRemaining } from "@/lib/format";
import { useExpiry } from "@/lib/useExpiry";

/**
 * Countdown of an offer on the dark bar (design: detail and passengers): neutral, amber with
 * less than 5 minutes, red once expired.
 */
export function HeaderExpiry({ expiresAt, compact = false }: { expiresAt: string; compact?: boolean }) {
  const { remaining, expired, warning } = useExpiry(expiresAt);
  const label = expired
    ? "Oferta vencida"
    : compact
      ? formatRemaining(remaining)
      : `Vence en ${formatRemaining(remaining)}`;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 font-mono text-[13px] font-semibold",
        compact && "px-2 py-1 text-[12px]",
        expired ? "bg-bad-soft text-bad" : warning ? "bg-warn-soft text-warn" : "bg-white/10 text-white",
      )}
    >
      {!compact && <ClockIcon width={14} height={14} />}
      {label}
    </span>
  );
}
