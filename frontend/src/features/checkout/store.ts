import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { onSessionEnd } from "@/lib/auth/tokens";
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
  /** User the drafts and attempts belong to: they hold personal data and bookings of that user. */
  owner: string | null;
  /** Makes the store the user's: if it held another user's drafts and attempts, they are dropped. */
  ownBy: (userId: string) => void;
  /** Forgets every draft and attempt (sign out). */
  clear: () => void;
  /** Passenger data typed for each trip item; kept if the fare expires or the page reloads. */
  drafts: Record<string, PassengerDraft>;
  /** Current attempt of each trip item. */
  attempts: Record<string, CheckoutAttempt>;
  /** Trip items whose passenger is the signed-in user (filled from the account). */
  holders: Record<string, boolean>;
  setHolder: (itemKey: string, isHolder: boolean) => void;
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
      owner: null,
      holders: {},
      setHolder: (itemKey, isHolder) => set({ holders: { ...get().holders, [itemKey]: isHolder } }),
      ownBy: (userId) => {
        if (get().owner !== userId) set({ owner: userId, drafts: {}, attempts: {}, holders: {} });
      },
      clear: () => set({ owner: null, drafts: {}, attempts: {}, holders: {} }),
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
        const { [itemKey]: _holder, ...holders } = get().holders;
        set({ drafts, attempts, holders });
      },
    }),
    {
      name: "booking-system.checkout",
      version: 2,
      storage: createJSONStorage(() => sessionStorage),
      partialize: ({ owner, drafts, attempts, holders }) => ({ owner, drafts, attempts, holders }),
      // Version 1 had no owner: its drafts could be another user's, so they are dropped.
      migrate: () => ({ owner: null, drafts: {}, attempts: {}, holders: {} }),
    },
  ),
);

// Signing out on a shared computer leaves no personal data of that user in the browser.
onSessionEnd((reason) => {
  if (reason === "signed_out") useCheckout.getState().clear();
});
