import { useNavigate } from "@tanstack/react-router";
import { useCallback } from "react";
import type { Fare, Flight } from "@/api/client";
import { useToasts } from "@/components/ui/toast";
import { fareName } from "@/lib/flights/fares";
import type { CompleteSearch } from "@/lib/flights/search";
import { makeTripItem, useTrip } from "./store";

/**
 * Saves a fare in "Tu viaje" and opens it. Idempotent: choosing the same offer again (back
 * button, double click) changes nothing; another fare of the same flight replaces it, with undo.
 */
export function useAddToTrip() {
  const add = useTrip((s) => s.add);
  const show = useToasts((s) => s.show);
  const navigate = useNavigate();

  // Stable across renders so memoized result cards don't re-render because of it.
  return useCallback(
    (flight: Flight, fare: Fare, search: CompleteSearch, searchId: string) => {
      const result = add(makeTripItem(flight, fare, search, searchId));
      if (result.status === "unchanged") {
        show({ message: "Este vuelo ya está en tu viaje." });
      } else if (result.status === "replaced") {
        const { previous } = result;
        const sameFare = fareName(previous.fare) === fareName(fare);
        show({
          message: sameFare
            ? "Actualizamos el precio de este vuelo en tu viaje."
            : `Cambiaste la tarifa a ${fareName(fare)}.`,
          action: { label: "Deshacer", onClick: () => add(previous) },
        });
      } else {
        show({ message: "Agregaste el vuelo a tu viaje." });
      }
      navigate({ to: "/trip" });
    },
    [add, show, navigate],
  );
}
