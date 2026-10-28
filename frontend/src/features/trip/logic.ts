import type { Money } from "@/api/client";
import type { Cell } from "@/lib/cell";
import { conditionCell } from "@/lib/flights/fares";
import type { TripItem } from "./store";

export function conditionsLine(item: TripItem): { text: string; tone: Cell["tone"] } {
  const change = conditionCell(item.fare.conditions.change);
  const refund = conditionCell(item.fare.conditions.refund);
  const changeText =
    change.tone === "ok"
      ? "Cambio gratis"
      : change.tone === "warn"
        ? `Cambio ${change.label}`
        : `Cambio: ${change.label.toLowerCase()}`;
  const refundText =
    refund.tone === "bad"
      ? "sin reembolso"
      : refund.tone === "ok"
        ? "reembolso gratis"
        : refund.tone === "warn"
          ? `reembolso ${refund.label}`
          : `reembolso: ${refund.label.toLowerCase()}`;
  const tone = change.tone === "ok" && refund.tone === "ok" ? "ok" : change.tone === "bad" ? "bad" : "warn";
  return { text: `${changeText} · ${refundText}`, tone };
}

/** Adds amounts per currency: offers in different currencies are never converted. */
export function totalsByCurrency(amounts: Money[]): Money[] {
  const totals = new Map<string, number>();
  for (const money of amounts) {
    totals.set(money.currency, (totals.get(money.currency) ?? 0) + Math.round(Number(money.amount) * 100));
  }
  return [...totals].map(([currency, cents]) => ({ currency, amount: (cents / 100).toFixed(2) }));
}
