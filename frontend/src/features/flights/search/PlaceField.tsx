import { type KeyboardEvent, useId, useState } from "react";
import type { PlaceSuggestion } from "@/api/client";
import { usePlaceSuggestions } from "@/api/flights";
import { CityIcon } from "@/components/icons";
import { cn } from "@/lib/cn";
import { placeLabel, rememberPlace } from "@/lib/placeLabels";
import { useDebounced } from "@/lib/useNow";
import { Field } from "./Field";

interface PlaceFieldProps {
  label: string;
  value: string | undefined;
  onChange: (code: string) => void;
  error?: string;
  className?: string;
}

/**
 * Airport or city autocomplete (ARIA combobox: arrows, Enter and Escape work).
 *
 * Design: the picked code in bold mono before the name; while typing, a 2 px blue border and a
 * panel "Destino · coincidencias para «…»". Names come from the airport database, in English.
 */
export function PlaceField({ label, value, onChange, error, className }: PlaceFieldProps) {
  const id = useId();
  const listId = `${id}-list`;
  const [text, setText] = useState("");
  const [editing, setEditing] = useState(false);
  const [active, setActive] = useState(0);
  const query = useDebounced(text, 200);
  const suggestions = usePlaceSuggestions(editing ? query : "");
  const options = suggestions.data ?? [];
  const open = editing && text.trim().length >= 2;
  const name = placeLabel(value);

  function select(place: PlaceSuggestion) {
    rememberPlace(place);
    onChange(place.code);
    setEditing(false);
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || options.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => (i + 1) % options.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => (i - 1 + options.length) % options.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const option = options[active];
      if (option) select(option);
    } else if (event.key === "Escape") {
      setEditing(false);
    }
  }

  return (
    <Field id={id} label={label} error={error} className={className}>
      <div
        className={cn(
          "flex h-12 items-center gap-2.5 rounded-md border bg-white px-3",
          "max-sm:h-auto max-sm:border-0 max-sm:bg-transparent max-sm:p-0",
          editing ? "sm:border-2 sm:border-action sm:px-[11px]" : error ? "border-bad" : "border-subtle",
        )}
      >
        {value && !editing && (
          <span className="data text-[16px] font-semibold text-ink max-sm:text-[15px]">{value}</span>
        )}
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && options[active] ? `${id}-opt-${active}` : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          autoComplete="off"
          placeholder="Ciudad o aeropuerto"
          value={editing ? text : (name ?? "")}
          onFocus={() => setEditing(true)}
          onBlur={() => window.setTimeout(() => setEditing(false), 150)}
          onChange={(e) => {
            setText(e.target.value);
            setEditing(true);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-ink outline-none placeholder:text-subtle"
        />
      </div>

      {open && (
        <div className="absolute top-full left-0 z-30 mt-1.5 w-[min(440px,calc(100vw-32px))] overflow-hidden rounded-lg border border-line bg-white shadow-pop">
          <p className="field-label border-b border-line-soft px-3.5 py-2.5">
            {label} · coincidencias para «{text.trim()}»
          </p>
          {options.length === 0 && (
            <p aria-live="polite" className="px-3.5 py-3 text-[14px] text-muted">
              {suggestions.isFetching
                ? "Buscando…"
                : "Sin coincidencias. Prueba con el código (por ejemplo, JFK)."}
            </p>
          )}
          <div id={listId} role="listbox" aria-label={`Sugerencias para ${label.toLowerCase()}`}>
            {options.map((place, i) => (
              // Keyboard is handled by the combobox input (aria-activedescendant), so options aren't focusable.
              // biome-ignore lint/a11y/useKeyWithClickEvents: see above.
              <div
                key={`${place.type}-${place.code}`}
                id={`${id}-opt-${i}`}
                role="option"
                tabIndex={-1}
                aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => select(place)}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  "flex cursor-pointer items-center gap-3 px-3.5 py-3 text-[14px]",
                  i > 0 && "border-t border-line-soft",
                  place.type === "airport" && "pl-11",
                  i === active && "bg-action-soft",
                )}
              >
                {place.type === "city" && <CityIcon className="shrink-0 text-action" />}
                {place.type === "city" ? (
                  <span className="flex-1">
                    <strong>{place.name}</strong> · todos los aeropuertos
                  </span>
                ) : (
                  <span className="min-w-0 flex-1">
                    {place.name}
                    <span className="block text-[12px] text-muted">
                      {[place.city, place.country_code].filter(Boolean).join(", ")}
                      {place.time_zone ? ` · ${place.time_zone}` : ""}
                    </span>
                  </span>
                )}
                <span className="data text-[14px] font-semibold">{place.code}</span>
              </div>
            ))}
          </div>
          <p className="border-t border-line-soft px-3.5 py-2.5 text-[12px] text-muted">
            Los nombres de ciudad y aeropuerto se muestran como figuran en la base de aeropuertos, en inglés.
          </p>
        </div>
      )}
    </Field>
  );
}
