import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ApiError } from "@/api/client";
import { AlertIcon, ClockIcon, SpinnerIcon } from "@/components/icons";
import { Dialog } from "@/components/ui/dialog";
import { cn } from "@/lib/cn";
import { formatRemaining } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { type FlightSearch, pickSearch, type ResultsSearch } from "../search/params";
import type { RelaxSuggestion, ResultFilters } from "./logic";

/** After this long the search is flagged as slow and can be cancelled (large round trips take ~25 s). */
export const SLOW_SEARCH_MS = 40_000;

/** Countdowns turn amber when less than this is left (design: "pasa a ámbar a los 5 min"). */
export const EXPIRY_WARNING_MS = 5 * 60_000;

const PRIMARY =
  "inline-flex h-11 items-center rounded-md bg-action px-4 font-semibold text-white hover:bg-action-hover hover:text-white";
const SECONDARY =
  "inline-flex h-11 items-center rounded-md border border-line bg-white px-4 text-ink hover:text-ink";

/** Skeleton of a result card, with the final card's shape so nothing jumps (design board "Espera"). */
function SkeletonCard({ opacity, w1, w2 }: { opacity: number; w1: string; w2: string }) {
  return (
    <div
      aria-hidden
      style={{ opacity }}
      className="grid rounded-lg border border-line bg-white sm:grid-cols-[minmax(0,1fr)_260px]"
    >
      <div className="flex flex-col gap-3 px-3.5 py-3 sm:px-6 sm:py-4">
        <span className="skeleton block h-3 max-w-[220px]" style={{ width: w1 }} />
        <div className="grid grid-cols-[52px_minmax(0,1fr)_52px] items-center gap-2.5 sm:grid-cols-[76px_minmax(0,1fr)_76px] sm:gap-[18px]">
          <span className="skeleton block h-6" />
          <span className="block border-t-2 border-dashed border-line" />
          <span className="skeleton block h-6" />
        </div>
        <span className="skeleton mx-auto block h-3 max-w-[240px] max-sm:hidden" style={{ width: w2 }} />
      </div>
      <div className="flex justify-between gap-2.5 border-t border-dashed border-line-dash px-3.5 py-2.5 sm:flex-col sm:justify-center sm:border-t-0 sm:border-l sm:px-6 sm:py-4">
        <span className="skeleton block h-3 w-[70%] max-sm:w-[90px]" />
        <span className="skeleton block h-[22px] w-[85%] max-sm:h-4 max-sm:w-[100px]" />
      </div>
    </div>
  );
}

const SKELETON_WIDTHS = ["70%", "55%", "80%", "62%", "50%"];

/** Waiting state (design board "Espera"). */
export function SearchingState({ onCancel }: { onCancel: () => void }) {
  const [startedAt] = useState(() => Date.now());
  const elapsed = useNow(1000) - startedAt;

  return (
    <section aria-busy="true" aria-live="polite" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2.5 rounded-lg border border-line bg-white px-[18px] py-3.5">
        <span className="flex items-center gap-2.5 text-[15px] font-semibold">
          <SpinnerIcon className="animate-spin text-action" />
          Consultando aerolíneas en paralelo…
        </span>
        <span className="data text-[14px] text-muted">{Math.floor(elapsed / 1000)} s</span>
        <ol className="flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-muted">
          <li className="font-semibold text-ok">✓ Búsqueda enviada</li>
          <li className="font-semibold text-ink">● Esperando respuestas</li>
          <li>○ Agrupando tarifas del mismo vuelo</li>
        </ol>
        <span className="w-full text-[13px] text-muted sm:hidden">Suele tardar entre 5 y 30 segundos.</span>
      </div>
      {elapsed > SLOW_SEARCH_MS && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-3 rounded-lg border border-warn-line bg-warn-soft px-4 py-3 text-[14px] text-warn-ink"
        >
          <span className="flex-1 font-semibold">Está tardando más de lo normal.</span>
          <button type="button" className={SECONDARY} onClick={onCancel}>
            Cancelar búsqueda
          </button>
        </div>
      )}
      <div aria-hidden className="flex flex-wrap gap-2 max-sm:hidden">
        {[130, 110, 120, 100].map((w) => (
          <span key={w} className="skeleton block h-[38px] rounded-md" style={{ width: w }} />
        ))}
      </div>
      {SKELETON_WIDTHS.map((w, i) => (
        <SkeletonCard key={w} opacity={1 - i * 0.15} w1={w} w2={SKELETON_WIDTHS[(i + 2) % 5] ?? w} />
      ))}
    </section>
  );
}

/** Provider failure or rejected criteria (design: red box). Never shows technical details. */
export function SearchErrorState({
  error,
  onRetry,
  search,
}: {
  error: unknown;
  onRetry: () => void;
  search: FlightSearch;
}) {
  const invalid = error instanceof ApiError && error.code === "invalid_search";
  const message = invalid
    ? (error as ApiError).message
    : error instanceof ApiError && error.code === "provider_timeout"
      ? "Las aerolíneas no respondieron a tiempo. Tu búsqueda quedó guardada."
      : "Hubo un problema al consultar las aerolíneas. Tu búsqueda quedó guardada.";

  return (
    <section role="alert" className="flex flex-col gap-2.5 rounded-lg border border-line bg-white p-5">
      <div className="flex gap-3 rounded-md border border-bad-line bg-bad-soft p-3.5">
        <AlertIcon className="shrink-0 text-bad" />
        <div className="flex flex-col gap-1.5 text-[14px] text-bad-ink">
          <strong>{invalid ? "Revisá los datos de la búsqueda" : "No pudimos completar la búsqueda"}</strong>
          <span>{message}</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {!invalid && (
          <button type="button" className={PRIMARY} onClick={onRetry}>
            Reintentar
          </button>
        )}
        <Link to="/" search={pickSearch(search)} className={SECONDARY}>
          Modificar búsqueda
        </Link>
      </div>
    </section>
  );
}

function shiftDate(iso: string | undefined, days: number): string | undefined {
  if (!iso) return undefined;
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

const OUTLINE =
  "inline-flex h-10 items-center rounded-md border border-action bg-white px-3 text-[13px] font-semibold text-action";
const PLAIN =
  "inline-flex h-10 items-center rounded-md border border-line bg-white px-3 text-[13px] text-ink";

/** The provider returned no flights: nearby dates and, if set, dropping "only direct". */
export function NoFlightsState({ search }: { search: ResultsSearch }) {
  const base = pickSearch(search);
  return (
    <section className="flex flex-col gap-2.5 rounded-lg border border-line bg-white p-5">
      <h2 className="text-[17px] font-semibold">No encontramos vuelos para esta fecha</h2>
      <div className="flex flex-wrap gap-2">
        {[-3, 3].map((days) => (
          <Link
            key={days}
            to="/flights"
            search={{ ...base, depart: shiftDate(base.depart, days), ret: shiftDate(base.ret, days) }}
            className={OUTLINE}
          >
            {days < 0 ? "Buscar 3 días antes" : "Buscar 3 días después"}
          </Link>
        ))}
        {search.direct && (
          <Link to="/flights" search={{ ...base, direct: undefined }} className={PLAIN}>
            Quitar «Solo vuelos directos»
          </Link>
        )}
      </div>
    </section>
  );
}

const FILTER_LABELS: Record<keyof ResultFilters, string> = {
  direct: "Vuelos directos",
  bag: "Con valija",
  refund: "Reembolsable",
  time: "Horario de salida",
  airlines: "Aerolínea",
};

const FILTER_PARAMS: Record<keyof ResultFilters, keyof ResultsSearch> = {
  direct: "fDirect",
  bag: "fBag",
  refund: "fRefund",
  time: "fTime",
  airlines: "fAirlines",
};

/** Filters left nothing (design): suggest which one to drop, with the flights that would show. */
export function NoMatchesState({
  suggestions,
  activeCount,
  total,
}: {
  suggestions: RelaxSuggestion[];
  activeCount: number;
  total: number;
}) {
  const navigate = useNavigate({ from: "/flights" });
  const clear = (patch: Partial<ResultsSearch>) =>
    navigate({ search: (prev) => ({ ...prev, ...patch }), replace: true });

  return (
    <section className="flex flex-col gap-2.5 rounded-lg border border-line bg-white p-5">
      <h2 className="text-[17px] font-semibold">
        Ningún vuelo cumple {activeCount === 1 ? "el filtro" : `los ${activeCount} filtros`}
      </h2>
      <p className="text-[14px] text-ink-2">Probá quitando uno; al lado ves cuántos vuelos aparecerían:</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s.filter}
            type="button"
            className={OUTLINE}
            onClick={() => clear({ [FILTER_PARAMS[s.filter]]: undefined })}
          >
            Quitar «{FILTER_LABELS[s.filter]}» → {s.count} {s.count === 1 ? "vuelo" : "vuelos"}
          </button>
        ))}
        <button
          type="button"
          className={PLAIN}
          onClick={() =>
            clear({
              fDirect: undefined,
              fBag: undefined,
              fRefund: undefined,
              fTime: undefined,
              fAirlines: undefined,
            })
          }
        >
          Limpiar filtros ({total})
        </button>
      </div>
    </section>
  );
}

const utcTime = (iso: string) => new Date(iso).toISOString().slice(11, 16);

/** Validity of the search's offers (design: box at the right of the filters). */
export function ExpiryBadge({ expiresAt }: { expiresAt: string }) {
  const remaining = new Date(expiresAt).getTime() - useNow(1000);
  if (remaining <= 0) return null;
  const warning = remaining < EXPIRY_WARNING_MS;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-md border px-3 py-2 text-[13px]",
        warning ? "border-warn-line bg-warn-soft text-warn-ink" : "border-line bg-white text-ink-2",
      )}
    >
      <ClockIcon />
      <span>
        <strong>Precios válidos por {formatRemaining(remaining)}.</strong> Después se vuelven a consultar.
      </span>
    </span>
  );
}

/** Offers expired (design: dialog). Refreshing keeps criteria, filters and the flight being looked at. */
export function ExpiredDialog({
  expiresAt,
  watching,
  onRefresh,
  refreshing,
  search,
}: {
  expiresAt: string;
  watching: string | null;
  onRefresh: () => void;
  refreshing: boolean;
  search: FlightSearch;
}) {
  const expired = new Date(expiresAt).getTime() <= useNow(1000);
  return (
    <Dialog open={expired} title="Los precios de esta búsqueda vencieron">
      <p className="text-[14px] text-ink-2">
        Las aerolíneas mantienen las ofertas unos 30 minutos (hasta las {utcTime(expiresAt)} UTC). Volvemos a
        buscar con los mismos datos y filtros
        {watching ? `, y te dejamos marcado el vuelo que estabas mirando: ${watching}` : ""}.
      </p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={PRIMARY} onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Actualizando…" : "Actualizar precios"}
        </button>
        <Link to="/" search={pickSearch(search)} className={SECONDARY}>
          Nueva búsqueda
        </Link>
      </div>
    </Dialog>
  );
}
