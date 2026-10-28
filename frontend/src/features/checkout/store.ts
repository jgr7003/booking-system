import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { PassengerDraft } from "./logic";

/**
 * A checkout attempt of one fare: the `Idempotency-Key` sent with it and, once created, its
 * booking. Retries of the same attempt (double click, network error, reload) reuse the key, so
 * the backend never books twice; a new attempt (after a failure) gets a new key.
 */
export interface CheckoutAttempt {
  offerId: string;
  idempotencyKey: string;
  bookingId?: string;
}

interface CheckoutState {
  /** Passenger data typed for each trip item; kept if the fare expires or the page reloads. */
  drafts: Record<string, PassengerDraft>;
  /** Current attempt of each trip item. */
  attempts: Record<string, CheckoutAttempt>;
  saveDraft: (itemKey: string, draft: PassengerDraft) => void;
  /** The attempt in progress for this fare, or a new one (also when the offer changed). */
  attemptFor: (itemKey: string, offerId: string) => CheckoutAttempt;
  setBooking: (itemKey: string, bookingId: string) => void;
  /** Ends the attempt: the next confirmation uses a new key. */
  endAttempt: (itemKey: string) => void;
  /** Forgets everything about the item (booked). */
  forget: (itemKey: string) => void;
}

export const useCheckout = create<CheckoutState>()(
  persist(
    (set, get) => ({
      drafts: {},
      attempts: {},
      saveDraft: (itemKey, draft) => set({ drafts: { ...get().drafts, [itemKey]: draft } }),
      attemptFor: (itemKey, offerId) => {
        const current = get().attempts[itemKey];
        if (current && current.offerId === offerId) return current;
        const attempt = { offerId, idempotencyKey: crypto.randomUUID() };
        set({ attempts: { ...get().attempts, [itemKey]: attempt } });
        return attempt;
      },
      setBooking: (itemKey, bookingId) => {
        const current = get().attempts[itemKey];
        if (current) set({ attempts: { ...get().attempts, [itemKey]: { ...current, bookingId } } });
      },
      endAttempt: (itemKey) => {
        const { [itemKey]: _ended, ...rest } = get().attempts;
        set({ attempts: rest });
      },
      forget: (itemKey) => {
        const { [itemKey]: _draft, ...drafts } = get().drafts;
        const { [itemKey]: _attempt, ...attempts } = get().attempts;
        set({ drafts, attempts });
      },
    }),
    {
      name: "booking-system.checkout",
      version: 1,
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ drafts, attempts }) => ({ drafts, attempts }),
    },
  ),
);
