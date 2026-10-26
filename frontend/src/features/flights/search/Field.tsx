import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface FieldProps {
  id: string;
  label: string;
  children: ReactNode;
  className?: string;
  /** Label of a field that doesn't apply (e.g. "Vuelta" on a one-way trip). */
  muted?: boolean;
  error?: string;
}

/**
 * Form field of the design.
 *
 * Desktop: uppercase label above a 48 px box. Mobile: the label goes inside a white card with
 * the value below it (design board "Mobile").
 */
export function Field({ id, label, children, className, muted, error }: FieldProps) {
  return (
    <div
      className={cn(
        "relative flex min-w-0 flex-col gap-1.5",
        "max-sm:gap-0.5 max-sm:rounded-lg max-sm:border max-sm:border-line max-sm:bg-white max-sm:px-3 max-sm:py-2.5",
        className,
      )}
    >
      <label htmlFor={id} className={cn("field-label max-sm:text-[11px]", muted && "text-muted-2")}>
        {label}
      </label>
      {children}
      {error && (
        <span id={`${id}-error`} className="text-[13px] text-bad">
          {error}
        </span>
      )}
    </div>
  );
}

/** Box of a control inside `Field` (input, select, button). */
export function controlClass({
  error,
  disabled,
  focused,
}: {
  error?: boolean;
  disabled?: boolean;
  focused?: boolean;
} = {}) {
  return cn(
    "flex h-12 w-full min-w-0 items-center rounded-md border bg-white px-3 text-left text-[15px] text-ink outline-none",
    "max-sm:h-auto max-sm:border-0 max-sm:bg-transparent max-sm:p-0 max-sm:text-[14px]",
    "focus-visible:border-2 focus-visible:border-action focus-visible:px-[11px]",
    "max-sm:focus-visible:border-0 max-sm:focus-visible:p-0",
    focused && "sm:border-2 sm:border-action sm:px-[11px]",
    error ? "border-bad" : "border-subtle",
    disabled && "border-dashed border-line-dash bg-surface-2 text-[14px] text-muted-2",
  );
}
