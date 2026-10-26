import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { useTrip } from "@/features/trip/store";
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
  vi.useRealTimers();
});

afterAll(() => server.close());
