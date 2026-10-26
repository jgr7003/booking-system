import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { FlightDetailPage } from "@/features/flights/detail/FlightDetailPage";
import { ResultsPage } from "@/features/flights/results/ResultsPage";
import {
  detailSearchSchema,
  flightSearchSchema,
  resultsSearchSchema,
} from "@/features/flights/search/params";
import { SearchPage } from "@/features/flights/search/SearchPage";
import { TripPage } from "@/features/trip/TripPage";

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

export const routeTree = rootRoute.addChildren([searchRoute, resultsRoute, detailRoute, tripRoute]);

export function createAppRouter() {
  return createRouter({ routeTree, defaultPreload: "intent", scrollRestoration: true });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
