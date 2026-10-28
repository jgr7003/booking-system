import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** Text box of the passengers and payment form (design: 44 px, gray border, red when invalid). */
export function inputClass(invalid: boolean, mono = false) {
  return cn(
    "h-11 w-full min-w-0 rounded-md border border-subtle bg-white px-3 text-[14px] font-normal text-ink outline-none",
    "focus-visible:border-2 focus-visible:border-action focus-visible:px-[11px]",
    "disabled:bg-surface-2 disabled:text-muted-2",
    mono && "font-mono",
    invalid && "border-2 border-bad-strong px-[11px]",
  );
}

/** Select of the form, with the same box as the inputs. */
export function selectClass(invalid: boolean, mono = false) {
  return cn(inputClass(invalid, mono), "px-2 focus-visible:px-[7px]", invalid && "px-[7px]");
}

/** Message under a field. */
export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <span id={id} className="text-[12px] font-normal text-bad">
      {message}
    </span>
  );
}

/** Label above its control, as in the design: 13 px semibold, 6 px apart. */
export function FormField({
  id,
  label,
  className,
  children,
}: {
  id: string;
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-[13px] font-semibold">
        {label}
      </label>
      {children}
    </div>
  );
}

/** White card with a titled bar (design: "Pasajero 1 · Adulto", "Cuándo pagar"). */
export function FormSection({
  id,
  title,
  aside,
  children,
}: {
  id: string;
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="overflow-hidden rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-line-soft px-[18px] py-3.5">
        <h2 id={id} className="text-[16px] font-semibold">
          {title}
        </h2>
        {aside && <span className="text-[13px] text-muted">{aside}</span>}
      </div>
      {children}
    </section>
  );
}
