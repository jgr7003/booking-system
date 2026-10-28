import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import {
  api,
  type Booking,
  type BookingRequest,
  type BookingStatus,
  type PriceDecisionRequest,
  unwrap,
} from "./client";

export const bookingKeys = {
  detail: (id: string) => ["bookings", id] as const,
};

/** States after which a booking never changes. */
const FINAL: ReadonlySet<BookingStatus> = new Set(["confirmed", "failed", "cancelled"]);

export function isFinal(status: BookingStatus): boolean {
  return FINAL.has(status);
}

/**
 * Without events (no `EventSource`, or the stream dropped), the booking is read again this often
 * while it isn't final: the plan B of the design (`GET /bookings/{id}`).
 */
export const BOOKING_POLL_MS = 5000;

export async function createBooking(body: BookingRequest, idempotencyKey: string): Promise<Booking> {
  return unwrap(
    await api.POST("/api/v1/flights/bookings", {
      body,
      params: { header: { "idempotency-key": idempotencyKey } },
    }),
  );
}

export async function getBooking(id: string): Promise<Booking> {
  return unwrap(
    await api.GET("/api/v1/flights/bookings/{booking_id}", { params: { path: { booking_id: id } } }),
  );
}

export async function decidePrice(id: string, body: PriceDecisionRequest): Promise<Booking> {
  return unwrap(
    await api.POST("/api/v1/flights/bookings/{booking_id}/price-decision", {
      body,
      params: { path: { booking_id: id } },
    }),
  );
}

/**
 * Books a fare. The caller keeps the `Idempotency-Key` of the checkout attempt: sending the
 * same one again (double click, retry after a network error) returns the same booking.
 */
export function useCreateBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ body, idempotencyKey }: { body: BookingRequest; idempotencyKey: string }) =>
      createBooking(body, idempotencyKey),
    onSuccess: (booking) => queryClient.setQueryData(bookingKeys.detail(booking.id), booking),
  });
}

/** Answers a new price ("Aceptar y continuar" or "Cancelar"). */
export function usePriceDecision(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PriceDecisionRequest) => decidePrice(id, body),
    onSuccess: (booking) => queryClient.setQueryData(bookingKeys.detail(booking.id), booking),
  });
}

/**
 * A booking and its current state (no request while `id` is `null`).
 *
 * While it isn't final it's polled slowly, as a safety net for lost events; the events of
 * `useBookingEvents` make it refresh right away.
 */
export function useBooking(id: string | null) {
  return useQuery({
    queryKey: id ? bookingKeys.detail(id) : ["bookings", "none"],
    queryFn: () => getBooking(id as string),
    enabled: id !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && isFinal(status) ? false : BOOKING_POLL_MS;
    },
  });
}

/**
 * Listens to the state changes of a booking (Server-Sent Events) and refreshes it on each one.
 *
 * An event only says "it changed": the booking is read again with `GET`, so a lost or repeated
 * event never shows a wrong state. The stream is closed by hand on a final state, because the
 * browser would reconnect on its own when the server closes it.
 */
export function useBookingEvents(id: string | null) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!id || typeof EventSource === "undefined") return;
    const source = new EventSource(`/api/v1/flights/bookings/${id}/events`);
    source.addEventListener("status", (event) => {
      const { status } = JSON.parse((event as MessageEvent<string>).data) as { status: BookingStatus };
      queryClient.invalidateQueries({ queryKey: bookingKeys.detail(id) });
      if (isFinal(status)) source.close();
    });
    return () => source.close();
  }, [id, queryClient]);
}
