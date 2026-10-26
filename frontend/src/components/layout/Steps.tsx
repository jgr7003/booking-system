import { Link } from "@tanstack/react-router";
import { Fragment } from "react";
import { cn } from "@/lib/cn";

const STEPS = ["Vuelos", "Tu viaje", "Pasajeros", "Pago"] as const;

const FUTURE =
  "flex h-[26px] w-[26px] items-center justify-center rounded-full border border-muted-2 font-mono text-[13px] text-line-strong";

/**
 * Steps of the booking flow as circles (design: results and "Tu viaje").
 * Done steps show ✓ and link back; the current one has a light ring.
 */
export function StepCircles({ current, canOpenTrip }: { current: number; canOpenTrip: boolean }) {
  return (
    <ol aria-label="Pasos" className="flex items-center">
      {STEPS.map((label, i) => {
        const done = i < current;
        const isCurrent = i === current;
        let circle = (
          <span title={label} className={FUTURE}>
            {i + 1}
          </span>
        );
        if (isCurrent) {
          circle = (
            <span
              title={label}
              className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-action font-mono font-semibold text-white shadow-[0_0_0_2px_#111827,0_0_0_4px_#93B4FF]"
            >
              {i + 1}
            </span>
          );
        } else if (done || (i === 1 && canOpenTrip)) {
          circle = (
            <Link
              to={i === 0 ? "/" : "/trip"}
              title={label}
              aria-label={`Paso ${i + 1}, ${label.toLowerCase()}${done ? ": completo" : ""}`}
              className={cn(
                done
                  ? "flex h-[26px] w-[26px] items-center justify-center rounded-full bg-action text-[13px] font-bold text-white hover:text-white"
                  : `${FUTURE} hover:border-white hover:text-white`,
              )}
            >
              {done ? "✓" : i + 1}
            </Link>
          );
        }
        return (
          <li key={label} aria-current={isCurrent ? "step" : undefined} className="flex items-center">
            {i > 0 && (
              <span
                aria-hidden
                className={cn("w-[22px]", i <= current ? "h-0.5 bg-action" : "h-px bg-header-line")}
              />
            )}
            {circle}
          </li>
        );
      })}
    </ol>
  );
}

/** Steps as text links (design: flight detail). */
export function StepLinks({ current }: { current: number }) {
  return (
    <nav aria-label="Pasos" className="flex flex-1 flex-wrap gap-x-3.5 gap-y-1.5 text-[13px] text-subtle">
      {STEPS.map((label, i) => {
        const text = `${i + 1} ${label}`;
        if (i === current) {
          return (
            <span key={label} aria-current="step" className="font-semibold text-white">
              {text}
            </span>
          );
        }
        if (i <= 1) {
          return (
            <Fragment key={label}>
              <Link to={i === 0 ? "/" : "/trip"} className="text-line-strong hover:text-white">
                {text}
              </Link>
            </Fragment>
          );
        }
        return <span key={label}>{text}</span>;
      })}
    </nav>
  );
}

/** "Paso 2 de 4" (design: mobile). */
export function StepCount({ current }: { current: number }) {
  return (
    <span className="font-mono text-[12px] text-line-strong">
      Paso {current + 1} de {STEPS.length}
    </span>
  );
}
