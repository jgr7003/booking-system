import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { BookingPage } from "@/features/booking/BookingPage";
import { CheckoutPage } from "@/features/checkout/CheckoutPage";
import { FlightDetailPage } from "@/features/flights/detail/FlightDetailPage";
import { ResultsPage } from "@/features/flights/results/ResultsPage";
import { SearchPage } from "@/features/flights/search/SearchPage";
import { TripPage } from "@/features/trip/TripPage";
import { detailSearchSchema, flightSearchSchema, resultsSearchSchema } from "@/lib/flights/search";

const rootRoute = createRootRoute({ component: AppLayout });

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: (search) => flightSearchSchema.parse(search),
  component: SearchPage,
});

const resultsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/flights",
  validateSearch: (search) => resultsSearchSchema.parse(search),
  component: ResultsPage,
});

const detailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/flights/$key",
  validateSearch: (search) => detailSearchSchema.parse(search),
  component: FlightDetailPage,
});

const tripRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/trip",
  component: TripPage,
});

const checkoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/checkout/$itemKey",
  component: CheckoutPage,
});

const bookingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bookings/$bookingId",
  component: BookingPage,
});

export const routeTree = rootRoute.addChildren([
  searchRoute,
  resultsRoute,
  detailRoute,
  tripRoute,
  checkoutRoute,
  bookingRoute,
]);

export function createAppRouter() {
  return createRouter({ routeTree, defaultPreload: "intent", scrollRestoration: true });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
