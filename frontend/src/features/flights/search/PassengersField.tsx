import { useId } from "react";
import { Popover, PopoverClose, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";
import { INFANT_MAX_AGE, MAX_CHILD_AGE, MAX_PASSENGERS } from "@/lib/flights/search";
import { formatPassengers } from "@/lib/format";
import { controlClass, Field } from "./Field";

export interface PassengersValue {
  adults: number;
  /** Age of each minor; `null` until chosen (the age changes the fare, so it's never assumed). */
  children: (number | null)[];
}

interface PassengersFieldProps {
  value: PassengersValue;
  onChange: (value: PassengersValue) => void;
  error?: string;
  /** Passengers that can be booked today, when fewer than airlines accept. */
  limit?: number;
}

const AGES = Array.from({ length: MAX_CHILD_AGE + 1 }, (_, age) => age);

const STEPPER =
  "flex h-11 w-11 items-center justify-center rounded-md border text-[18px] disabled:border-line disabled:bg-surface-2 disabled:text-subtle";
const STEPPER_ON = "border-action bg-white text-action";

/** Adults and minors with their age. Blocks a second infant per adult and explains why. */
export function PassengersField({ value, onChange, error, limit = MAX_PASSENGERS }: PassengersFieldProps) {
  const id = useId();
  const total = value.adults + value.children.length;
  const max = Math.min(limit, MAX_PASSENGERS);
  const infants = value.children.filter((age) => age !== null && age <= INFANT_MAX_AGE).length;

  function setChild(index: number, age: number | null) {
    onChange({ ...value, children: value.children.map((a, i) => (i === index ? age : a)) });
  }

  return (
    <Field id={id} label="Pasajeros" error={error}>
      <Popover>
        <PopoverTrigger
          id={id}
          className={cn(
            controlClass({ error: Boolean(error) }),
            "text-[14px] font-medium max-sm:font-normal",
          )}
        >
          {formatPassengers(value.adults, value.children.length)}
        </PopoverTrigger>
        <PopoverContent
          aria-label="Pasajeros"
          className="flex w-[min(420px,calc(100vw-32px))] flex-col gap-3.5 p-4"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-[14px]">
              <strong>Adultos</strong>
              <span className="block text-[12px] text-muted">18 años o más</span>
            </span>
            <span className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Quitar adulto"
                disabled={value.adults <= 1 || value.adults <= infants}
                onClick={() => onChange({ ...value, adults: value.adults - 1 })}
                className={cn(STEPPER, STEPPER_ON)}
              >
                −
              </button>
              <span className="data w-4 text-center font-semibold" aria-live="polite">
                {value.adults}
              </span>
              <button
                type="button"
                aria-label="Agregar adulto"
                disabled={total >= max}
                onClick={() => onChange({ ...value, adults: value.adults + 1 })}
                className={cn(STEPPER, STEPPER_ON)}
              >
                +
              </button>
            </span>
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-line-soft pt-3.5">
            <span className="text-[14px]">
              <strong>Menores</strong>
              <span className="block text-[12px] text-muted">0 a 17 años, con su edad el día del vuelo</span>
            </span>
            <button
              type="button"
              disabled={total >= max}
              onClick={() => onChange({ ...value, children: [...value.children, null] })}
              className="h-11 shrink-0 rounded-md border border-action bg-white px-3.5 text-[14px] font-semibold text-action disabled:border-line disabled:text-subtle"
            >
              + Agregar menor
            </button>
          </div>

          {value.children.map((age, index) => {
            // An infant age is only possible if there's a free adult (each infant needs its own).
            const othersInfants = infants - (age !== null && age <= INFANT_MAX_AGE ? 1 : 0);
            const infantBlocked = othersInfants >= value.adults;
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: minors have no identity besides their position.
              <div key={index} className="flex items-center gap-2">
                <label className="flex flex-1 items-center gap-2 text-[14px]">
                  <span className="w-20">Menor {index + 1}</span>
                  <select
                    value={age ?? ""}
                    onChange={(e) => setChild(index, e.target.value === "" ? null : Number(e.target.value))}
                    className="h-11 flex-1 rounded-md border border-subtle bg-white px-2"
                  >
                    <option value="">Edad</option>
                    {AGES.map((a) => (
                      <option key={a} value={a} disabled={a <= INFANT_MAX_AGE && infantBlocked}>
                        {a === 0 ? "Menos de 1 año" : `${a} ${a === 1 ? "año" : "años"}`}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  aria-label={`Quitar menor ${index + 1}`}
                  onClick={() =>
                    onChange({ ...value, children: value.children.filter((_, i) => i !== index) })
                  }
                  className="h-11 rounded-md px-3 text-[13px] font-semibold text-bad hover:bg-bad-soft"
                >
                  Quitar
                </button>
              </div>
            );
          })}

          {max < MAX_PASSENGERS && (
            <p className="rounded-md bg-action-tint px-3 py-2.5 text-[12px] leading-normal text-ink-2">
              Por ahora se reserva un viaje para {max === 1 ? "una persona adulta" : `${max} personas`}. Más
              pasajeros, próximamente.
            </p>
          )}
          <p className="rounded-md bg-canvas px-3 py-2.5 text-[12px] leading-normal text-muted">
            Cada menor de 0 o 1 año viaja en brazos de un adulto distinto.
            {infants >= value.adults && value.children.length > 0
              ? " Para sumar otro infante, agrega un adulto."
              : ` Con ${value.adults} ${value.adults === 1 ? "adulto se puede" : "adultos se pueden"} sumar ${value.adults - infants} ${value.adults - infants === 1 ? "infante" : "infantes"} más.`}
            {total >= MAX_PASSENGERS &&
              ` Las aerolíneas aceptan hasta ${MAX_PASSENGERS} pasajeros por reserva.`}
          </p>
          <PopoverClose className="h-11 self-end rounded-md bg-ink px-[18px] text-[14px] font-semibold text-white">
            Listo
          </PopoverClose>
        </PopoverContent>
      </Popover>
    </Field>
  );
}
