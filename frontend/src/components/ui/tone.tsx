import type { Cell, Tone } from "@/lib/cell";
import { cn } from "@/lib/cn";

const PILLS: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  na: "bg-canvas text-muted outline-1 -outline-offset-1 outline-dashed outline-subtle",
};

const TEXTS: Record<Tone, string> = {
  ok: "font-semibold text-ok",
  warn: "font-semibold text-warn",
  bad: "font-semibold text-bad",
  na: "italic text-muted",
};

/** Value as a colored block (design: fare matrix of the results). */
export function ToneCell({ cell, className, title }: { cell: Cell; className?: string; title?: string }) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center rounded px-2 py-1.5 font-semibold",
        PILLS[cell.tone],
        className,
      )}
    >
      {cell.label}
    </span>
  );
}

/** Value as colored text (design: fare table and conditions of the detail). */
export function ToneText({ cell, className }: { cell: Cell; className?: string }) {
  return <span className={cn(TEXTS[cell.tone], className)}>{cell.label}</span>;
}

export function toneTextClass(tone: Tone): string {
  return TEXTS[tone];
}
