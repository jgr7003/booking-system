/** What a fare includes (bags, change, refund) and how each value is shown. Shared by every screen. */
import type { Fare, FareCondition } from "@/api/client";
import type { Cell } from "@/lib/cell";
import { formatPenalty, isZero } from "@/lib/format";

/** Checked bags of the fare on the whole trip: the lowest of every slice and passenger; `null` if any is unknown. */
export function fareCheckedBags(fare: Fare): number | null {
  return lowest(fare.slices.flatMap((s) => s.baggage.map((b) => b.checked ?? null)));
}

/** Cabin bags of the fare on the whole trip; `null` if any is unknown. */
export function fareCarryOn(fare: Fare): number | null {
  return lowest(fare.slices.flatMap((s) => s.baggage.map((b) => b.carry_on ?? null)));
}

/** Lowest of the quantities; `null` (unknown) if there are none or any is unknown. */
export function lowest(values: (number | null | undefined)[]): number | null {
  if (values.length === 0 || values.some((v) => v === null || v === undefined)) return null;
  return Math.min(...(values as number[]));
}

/** "Con valija" only counts a checked bag the airline reports; unknown doesn't count. */
export function fareHasCheckedBag(fare: Fare): boolean {
  return (fareCheckedBags(fare) ?? 0) >= 1;
}

export function fareIsRefundable(fare: Fare): boolean {
  return fare.conditions.refund.allowed === true;
}

/** Fare names of every slice, e.g. "Economy Light" or "Basic / Economy Flex". */
export function fareName(fare: Fare): string {
  const names = [...new Set(fare.slices.map((s) => s.fare_brand).filter(Boolean))];
  return names.length ? names.join(" / ") : "Tarifa";
}

/** `null` → «Sin dato»; 0 → «No incluida»; n → «n incluida(s)». */
export function bagCell(quantity: number | null, kind: "checked" | "carry_on"): Cell {
  if (quantity === null) return { label: "Sin dato", tone: "na" };
  const [one, many, none] =
    kind === "checked" ? ["incluida", "incluidas", "No incluida"] : ["incluido", "incluidos", "No incluido"];
  if (quantity === 0) return { label: none, tone: "bad" };
  return { label: `${quantity} ${quantity === 1 ? one : many}`, tone: "ok" };
}

/** Change or refund: «No permite», «Gratis», the penalty in its own currency, or «Sin dato». */
export function conditionCell(condition: FareCondition): Cell {
  if (condition.allowed === false) return { label: "No permite", tone: "bad" };
  if (condition.allowed !== true) return { label: "Sin dato", tone: "na" };
  if (!condition.penalty) return { label: "Permite · cargo sin dato", tone: "na" };
  if (isZero(condition.penalty)) return { label: "Gratis", tone: "ok" };
  return { label: formatPenalty(condition.penalty), tone: "warn" };
}
