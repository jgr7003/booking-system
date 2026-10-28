import { useMutation, useQueryClient } from "@tanstack/react-query";
import { flightKeys, searchFlights } from "@/api/flights";
import { useToasts } from "@/components/ui/toast";
import { fareName } from "@/lib/flights/fares";
import { toCriteria } from "@/lib/flights/search";
import { formatMoney } from "@/lib/format";
import { makeTripItem, type TripItem, useTrip } from "./store";

/**
 * Refreshes the price of an expired item: searches again and, if the same flight still has a fare
 * with the same name, replaces the item with it. The outcome is told with a toast.
 */
export function useRefreshTripItem(item: TripItem) {
  const add = useTrip((s) => s.add);
  const show = useToasts((s) => s.show);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => {
      // A new search: the previous offers expired, so the cached results can't be reused.
      const criteria = toCriteria(item.search);
      return queryClient.fetchQuery({
        queryKey: flightKeys.search(criteria),
        queryFn: ({ signal }) => searchFlights(criteria, signal),
        staleTime: 0,
      });
    },
    onSuccess: (fresh) => {
      const sameFlight = fresh.flights.find((f) => f.key === item.flight.key);
      const sameFare = sameFlight?.fares.find((f) => fareName(f) === fareName(item.fare));
      if (sameFlight && sameFare) {
        add(makeTripItem(sameFlight, sameFare, item.search, fresh.search_id));
        show({ message: `Precio actualizado: ${formatMoney(sameFare.price.total)}.` });
      } else {
        show({ message: "Ese vuelo o tarifa ya no está disponible. Elegí otra opción en los resultados." });
      }
    },
    onError: () => show({ message: "No pudimos actualizar el precio. Probá de nuevo en unos segundos." }),
  });

  return { refresh: () => mutation.mutate(), refreshing: mutation.isPending };
}
