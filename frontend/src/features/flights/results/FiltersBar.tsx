import { useNavigate } from "@tanstack/react-router";
import { Chip } from "@/components/ui/chip";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { ResultsSearch } from "@/lib/flights/search";
import { type SortKey, TIME_WINDOW_LABELS, type TimeWindow } from "./logic";

const SORT_LABELS: Record<SortKey, string> = {
  price: "Menor precio",
  duration: "Menor duración",
  departure: "Salida más temprana",
};

function useUpdateSearch() {
  const navigate = useNavigate({ from: "/flights" });
  return (patch: Partial<ResultsSearch>) =>
    navigate({ search: (prev) => ({ ...prev, ...patch, hl: undefined }), replace: true });
}

/** "Ordenar por" select (design: right of the title). State lives in the URL. */
export function SortSelect({ search }: { search: ResultsSearch }) {
  const update = useUpdateSearch();
  return (
    <label className="inline-flex items-center gap-2 text-[14px] text-ink-2">
      <span className="max-sm:sr-only">Ordenar por</span>
      <select
        value={search.sort ?? "price"}
        onChange={(e) => update({ sort: e.target.value as SortKey })}
        className="h-10 rounded-md border border-subtle bg-white px-2.5 font-semibold text-ink"
      >
        {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
          <option key={key} value={key}>
            {SORT_LABELS[key]}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Filter buttons (design). Their state lives in the URL, so it survives reloads and "Actualizar precios". */
export function FilterChips({
  search,
  airlines,
}: {
  search: ResultsSearch;
  airlines: { code: string; name: string }[];
}) {
  const update = useUpdateSearch();
  const selectedAirlines = search.fAirlines ?? [];

  return (
    <>
      <Chip
        pressed={Boolean(search.fDirect)}
        onClick={() => update({ fDirect: search.fDirect ? undefined : true })}
      >
        Vuelos directos
      </Chip>
      <Chip pressed={Boolean(search.fBag)} onClick={() => update({ fBag: search.fBag ? undefined : true })}>
        Con valija
      </Chip>
      <Chip
        pressed={Boolean(search.fRefund)}
        onClick={() => update({ fRefund: search.fRefund ? undefined : true })}
      >
        Reembolsable
      </Chip>
      {airlines.length > 1 && (
        <Popover>
          <PopoverTrigger asChild>
            <Chip pressed={selectedAirlines.length > 0} mark={selectedAirlines.length ? "×" : "+"}>
              Aerolínea{selectedAirlines.length ? ` (${selectedAirlines.length})` : ""}
            </Chip>
          </PopoverTrigger>
          <PopoverContent aria-label="Aerolínea" className="w-64">
            <fieldset className="flex flex-col gap-2">
              <legend className="field-label mb-1">Aerolínea que vende</legend>
              {airlines.map((airline) => (
                <label key={airline.code} className="flex items-center gap-2 text-[14px]">
                  <input
                    type="checkbox"
                    className="h-[18px] w-[18px] accent-action"
                    checked={selectedAirlines.includes(airline.code)}
                    onChange={(e) => {
                      const next = e.target.checked
                        ? [...selectedAirlines, airline.code]
                        : selectedAirlines.filter((c) => c !== airline.code);
                      update({ fAirlines: next.length ? next : undefined });
                    }}
                  />
                  {airline.name}
                  <span className="data ml-auto text-[12px] text-muted">{airline.code}</span>
                </label>
              ))}
            </fieldset>
          </PopoverContent>
        </Popover>
      )}
      <Popover>
        <PopoverTrigger asChild>
          <Chip pressed={Boolean(search.fTime)} mark={search.fTime ? "×" : "+"}>
            {search.fTime ? TIME_WINDOW_LABELS[search.fTime].split(" (")[0] : "Horario de salida"}
          </Chip>
        </PopoverTrigger>
        <PopoverContent aria-label="Horario de salida" className="w-72">
          <fieldset className="flex flex-col gap-2">
            <legend className="field-label mb-1">Horario de salida</legend>
            {(Object.keys(TIME_WINDOW_LABELS) as TimeWindow[]).map((window) => (
              <label key={window} className="flex items-center gap-2 text-[14px]">
                <input
                  type="radio"
                  name="time-window"
                  className="h-[18px] w-[18px] accent-action"
                  checked={search.fTime === window}
                  onChange={() => update({ fTime: window })}
                />
                {TIME_WINDOW_LABELS[window]}
              </label>
            ))}
            <button
              type="button"
              className="self-start text-[13px] font-semibold text-action"
              onClick={() => update({ fTime: undefined })}
            >
              Cualquier horario
            </button>
          </fieldset>
        </PopoverContent>
      </Popover>
    </>
  );
}
