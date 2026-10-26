import { useNavigate } from "@tanstack/react-router";
import { type FormEvent, useId, useState } from "react";
import type { CabinClass } from "@/api/client";
import { cn } from "@/lib/cn";
import { DateField } from "./DateField";
import { controlClass, Field } from "./Field";
import { PassengersField, type PassengersValue } from "./PassengersField";
import { PlaceField } from "./PlaceField";
import { CABIN_LABELS, CABINS, type FlightSearch, searchErrors, todayIso } from "./params";

interface SearchFormProps {
  initial: FlightSearch;
}

/**
 * Search form (design board "Búsqueda").
 *
 * Desktop: trip type as a segmented control and the fields in an auto-fit grid where origin and
 * destination take two columns. Mobile: origin and destination share a card, then a 2×2 grid.
 */
export function SearchForm({ initial }: SearchFormProps) {
  const navigate = useNavigate();
  const cabinId = useId();
  // Round trip by default; a one-way search being modified stays one way.
  const [roundTrip, setRoundTrip] = useState(Boolean(initial.ret) || !initial.depart);
  const [from, setFrom] = useState(initial.from);
  const [to, setTo] = useState(initial.to);
  const [depart, setDepart] = useState(initial.depart ?? "");
  const [ret, setRet] = useState(initial.ret ?? "");
  const [passengers, setPassengers] = useState<PassengersValue>({
    adults: initial.adults ?? 1,
    children: initial.children ?? [],
  });
  const [cabin, setCabin] = useState<CabinClass>(initial.cabin ?? "economy");
  const [direct, setDirect] = useState(Boolean(initial.direct));
  const [submitted, setSubmitted] = useState(false);

  const today = todayIso();
  const missingAge = passengers.children.some((age) => age === null);
  const search: FlightSearch = {
    from,
    to,
    depart: depart || undefined,
    ret: roundTrip && ret ? ret : undefined,
    adults: passengers.adults,
    children: passengers.children.filter((a): a is number => a !== null),
    cabin,
    direct: direct || undefined,
  };
  const errors = searchErrors(search, today);
  if (roundTrip && !ret) errors.ret = "Elegí la fecha de vuelta o cambiá a solo ida.";
  if (missingAge) errors.adults = "Elegí la edad de cada menor.";
  const shownErrors = submitted ? errors : {};

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (Object.keys(errors).length > 0) return;
    navigate({
      to: "/flights",
      search: { ...search, children: search.children?.length ? search.children : undefined },
    });
  }

  const directCheckbox = (className: string) => (
    <label className={cn("items-center gap-2 text-[14px]", className)}>
      <input
        type="checkbox"
        checked={direct}
        onChange={(e) => setDirect(e.target.checked)}
        className="h-[18px] w-[18px] accent-action"
      />
      Solo vuelos directos
    </label>
  );

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-label="Buscar vuelos"
      className="flex flex-col gap-4 sm:rounded-lg sm:border sm:border-line sm:bg-white sm:p-5"
    >
      <div className="flex flex-wrap items-center gap-6">
        <fieldset className="flex overflow-hidden rounded-md border border-line bg-white max-sm:w-full">
          <legend className="sr-only">Tipo de viaje</legend>
          {[
            { label: "Solo ida", value: false },
            { label: "Ida y vuelta", value: true },
          ].map((option, i) => (
            <label
              key={option.label}
              className={cn(
                "flex h-10 cursor-pointer items-center gap-2 px-3.5 text-[14px] max-sm:h-11 max-sm:flex-1 max-sm:justify-center",
                i > 0 && "border-l border-line",
                roundTrip === option.value && "bg-ink font-semibold text-white",
              )}
            >
              <input
                type="radio"
                name="trip-type"
                checked={roundTrip === option.value}
                onChange={() => setRoundTrip(option.value)}
                className="accent-white max-sm:sr-only"
              />
              {option.label}
            </label>
          ))}
        </fieldset>
        {directCheckbox("hidden sm:flex")}
      </div>

      <div className="grid items-end gap-2.5 sm:[grid-template-columns:repeat(auto-fit,minmax(150px,1fr))]">
        {/* Mobile: one card with origin and destination; desktop: two grid cells each. */}
        <div className="overflow-visible max-sm:rounded-lg max-sm:border max-sm:border-line max-sm:bg-white sm:contents">
          <PlaceField
            label="Origen"
            value={from}
            onChange={setFrom}
            error={shownErrors.from}
            className="sm:col-span-2 max-sm:rounded-none max-sm:border-0"
          />
          <PlaceField
            label="Destino"
            value={to}
            onChange={setTo}
            error={shownErrors.to}
            className="sm:col-span-2 max-sm:rounded-none max-sm:border-0 max-sm:border-t max-sm:border-line-soft"
          />
        </div>

        <div className="grid grid-cols-2 gap-2 max-sm:mt-1.5 sm:contents">
          <DateField label="Ida" value={depart} min={today} onChange={setDepart} error={shownErrors.depart} />
          <DateField
            label="Vuelta"
            value={ret}
            min={depart || today}
            onChange={setRet}
            disabledText={roundTrip ? undefined : "Solo ida"}
            error={shownErrors.ret}
          />
          <PassengersField value={passengers} onChange={setPassengers} error={shownErrors.adults} />
          <Field id={cabinId} label="Cabina">
            <select
              id={cabinId}
              value={cabin}
              onChange={(e) => setCabin(e.target.value as CabinClass)}
              className={cn(controlClass(), "px-2.5 text-[14px]")}
            >
              {CABINS.map((c) => (
                <option key={c} value={c}>
                  {CABIN_LABELS[c]}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {directCheckbox("flex py-1 sm:hidden")}

        <button
          type="submit"
          className="h-12 rounded-md bg-action px-5 text-[15px] font-semibold text-white hover:bg-action-hover max-sm:h-[50px] max-sm:text-[16px]"
        >
          Buscar
        </button>
      </div>
    </form>
  );
}
