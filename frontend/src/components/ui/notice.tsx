import type { ReactNode } from "react";
import { AlertIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

const TONES = {
  warn: "border-warn-line bg-warn-soft text-warn-ink",
  bad: "border-bad-line bg-bad-soft text-bad-ink",
};

/** Amber or red box with an alert icon, a bold title and a line (design: checkout and confirmation). */
export function Notice({
  tone,
  title,
  role = "alert",
  className,
  children,
}: {
  tone: keyof typeof TONES;
  title: string;
  /** `alert` interrupts the screen reader; `status` waits its turn (for something that just takes long). */
  role?: "alert" | "status";
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      role={role}
      className={cn("flex items-start gap-3 rounded-lg border px-4 py-3 text-[14px]", TONES[tone], className)}
    >
      <AlertIcon className="mt-0.5 shrink-0" />
      <span className="flex flex-col gap-0.5">
        <strong>{title}</strong>
        <span>{children}</span>
      </span>
    </div>
  );
}
