import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  pressed: boolean;
  /** Mark after the label: "+" to add, "×" to remove, "▾" for a menu. */
  mark?: string;
}

/** Filter button of the design: "Con valija +" / "Con valija ×". */
export const Chip = forwardRef<HTMLButtonElement, ChipProps>(function Chip(
  { pressed, mark, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      aria-pressed={props["aria-haspopup"] ? undefined : pressed}
      className={cn(
        "inline-flex h-[38px] shrink-0 items-center gap-2 rounded-md border px-3 text-[14px] max-sm:h-[34px] max-sm:px-2.5 max-sm:text-[13px]",
        pressed
          ? "border-action bg-action-soft font-semibold text-action-hover"
          : "border-subtle bg-white text-ink hover:border-ink-2",
        className,
      )}
      {...props}
    >
      {children}
      <span aria-hidden className="text-[16px] leading-none">
        {mark ?? (pressed ? "×" : "+")}
      </span>
    </button>
  );
});
