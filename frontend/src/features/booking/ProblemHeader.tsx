import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const TONES = {
  bad: { box: "border-bad-line bg-bad-soft", badge: "bg-bad", ink: "text-bad-ink-2" },
  warn: { box: "border-warn-line bg-warn-soft", badge: "bg-warn", ink: "text-warn-ink" },
};

/** Colored band at the top of a booking that didn't end well (design: state 5, «no se pudo reservar»). */
export function ProblemHeader({
  tone,
  icon,
  title,
  subtitle,
}: {
  tone: keyof typeof TONES;
  icon: ReactNode;
  title: string;
  subtitle: ReactNode;
}) {
  const colors = TONES[tone];
  return (
    <div className={cn("flex items-center gap-3.5 border-b px-6 py-4 max-sm:px-4", colors.box)}>
      <span
        className={cn(
          "inline-flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full text-white",
          colors.badge,
        )}
      >
        {icon}
      </span>
      <div className="flex flex-col gap-0.5">
        <h1 className={cn("text-[18px] font-bold sm:text-[22px]", colors.ink)}>{title}</h1>
        <span className={cn("text-[15px]", colors.ink)}>{subtitle}</span>
      </div>
    </div>
  );
}
