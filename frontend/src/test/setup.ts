import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { setEventStreamFactory } from "@/api/eventStream";
import { useCheckout } from "@/features/checkout/store";
import { useTrip } from "@/features/trip/public";
import { resetSessionForTests } from "@/lib/auth/tokens";
import { server } from "./server";

// Any request (or WebSocket frame) without a handler fails: tests never reach a real API.
// MSW 3 renamed `onUnhandledRequest` to `onUnhandledFrame`; its default only warns.
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));

// jsdom has no layout: scrolling is a no-op instead of a "not implemented" error.
window.scrollTo = () => {};

afterEach(() => {
  cleanup();
  server.resetHandlers();
  sessionStorage.clear();
  useTrip.getState().clear();
  useCheckout.setState({ owner: null, drafts: {}, attempts: {}, holders: {} });
  vi.useRealTimers();
  vi.unstubAllGlobals();
  setEventStreamFactory(null);
  resetSessionForTests();
});

afterAll(() => server.close());
