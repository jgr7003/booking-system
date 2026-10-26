import { useId, useRef } from "react";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { controlClass, Field } from "./Field";

interface DateFieldProps {
  label: string;
  value: string;
  min: string;
  onChange: (value: string) => void;
  /** Shown instead of a date picker when the field doesn't apply (one-way trips). */
  disabledText?: string;
  error?: string;
}

/**
 * Date in the design's format ("mar 15 dic 2026", mono).
 *
 * The native date input does the work (keyboard, system calendar, accessibility) with its text
 * hidden; the formatted date is drawn on top of it.
 */
export function DateField({ label, value, min, onChange, disabledText, error }: DateFieldProps) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);

  if (disabledText) {
    return (
      <Field
        id={id}
        label={label}
        muted
        className="max-sm:border-dashed max-sm:border-line-dash max-sm:bg-surface-2"
      >
        <input id={id} disabled value={disabledText} className={controlClass({ disabled: true })} />
      </Field>
    );
  }

  return (
    <Field id={id} label={label} error={error}>
      <div className="relative">
        <input
          id={id}
          ref={input}
          type="date"
          value={value}
          min={min}
          onChange={(e) => onChange(e.target.value)}
          onClick={() => input.current?.showPicker?.()}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className={cn(
            controlClass({ error: Boolean(error) }),
            "cursor-pointer font-mono text-[14px] font-medium [&::-webkit-calendar-picker-indicator]:opacity-0",
            // With a date, the native "dd/mm/aaaa" fields are hidden entirely (also their focus
            // highlight) and the formatted date is drawn instead. Without one, the native field shows.
            value && "text-transparent caret-transparent [&::-webkit-datetime-edit]:opacity-0",
          )}
        />
        {value && (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-3 flex items-center font-mono text-[14px] font-medium text-ink max-sm:left-0"
          >
            {formatDate(value)}
          </span>
        )}
      </div>
    </Field>
  );
}
