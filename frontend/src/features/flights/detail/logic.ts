import type { Fare, FlightSegment } from "@/api/client";
import type { Cell, Tone } from "@/lib/cell";
import { conditionCell } from "@/lib/flights/fares";

export function amenityRows(segment: FlightSegment): { k: string; cell: Cell }[] {
  const amenities = segment.cabin?.amenities;
  if (!amenities) return [{ k: "Comodidades", cell: { label: "Sin informar", tone: "na" } }];
  const wifi: Record<string, Cell> = {
    free: { label: "Gratis", tone: "ok" },
    paid: { label: "Pago", tone: "warn" },
    available: { label: "Disponible", tone: "ok" },
    unavailable: { label: "No disponible", tone: "bad" },
  };
  const legroom: Record<string, [string, Tone]> = {
    less: ["menos espacio", "warn"],
    standard: ["estándar", "ok"],
    more: ["más espacio", "ok"],
  };
  const [space, spaceTone] = amenities.legroom
    ? (legroom[amenities.legroom] ?? [amenities.legroom, "na"])
    : [null, "na" as Tone];
  const seat: Cell = amenities.seat_pitch
    ? { label: `${amenities.seat_pitch}″ · ${space ?? "espacio sin dato"}`, tone: space ? spaceTone : "na" }
    : { label: "Sin dato", tone: "na" };
  return [
    {
      k: "Wi-Fi",
      cell: amenities.wifi
        ? (wifi[amenities.wifi] ?? { label: "Sin dato", tone: "na" })
        : { label: "Sin dato", tone: "na" },
    },
    {
      k: "Enchufe",
      cell:
        amenities.power === true
          ? { label: "Sí", tone: "ok" }
          : amenities.power === false
            ? { label: "No", tone: "bad" }
            : { label: "Sin dato", tone: "na" },
    },
    { k: "Asiento", cell: seat },
  ];
}

/** Change or refund in the detail's words: "Con cargo · GBP 300,00". */
export function penaltyCell(condition: Fare["conditions"]["change"]): Cell {
  const cell = conditionCell(condition);
  return cell.tone === "warn" ? { ...cell, label: `Con cargo · ${cell.label}` } : cell;
}

export function benefitCell(value: boolean | null | undefined, yes: string): Cell {
  if (value === true) return { label: yes, tone: "ok" };
  if (value === false) return { label: "No incluido", tone: "bad" };
  return { label: "Sin dato", tone: "na" };
}
