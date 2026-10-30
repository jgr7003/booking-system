import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { z } from "zod";
import { AppLayout } from "@/components/layout/AppLayout";
import { RequireSession } from "@/components/layout/RequireSession";
import { DevicesPage } from "@/features/account/DevicesPage";
import { AccountNotFoundPage } from "@/features/auth/AccountNotFoundPage";
import { CallbackPage } from "@/features/auth/CallbackPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { ForgotPasswordPage, SetPasswordPage, VerifyEmailPage } from "@/features/auth/PasswordPages";
import { SignupPage } from "@/features/auth/SignupPage";
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
  // Booking needs a session: without one it goes to the sign in and comes back with the trip saved.
  component: () => (
    <RequireSession>
      <CheckoutPage />
    </RequireSession>
  ),
});

const bookingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bookings/$bookingId",
  component: () => (
    <RequireSession>
      <BookingPage />
    </RequireSession>
  ),
});

// Query parameters of the account screens (03-usuarios-y-acceso.md §14), all optional text.
const authSearchSchema = z.object({
  return_to: z.string().optional(),
  email: z.string().optional(),
  error: z.string().optional(),
  attempt: z.string().optional(),
  provider: z.string().optional(),
  provider_name: z.string().optional(),
  token: z.string().optional(),
  kind: z.string().optional(),
  code: z.string().optional(),
  state: z.string().optional(),
});

const authSearch = (search: Record<string, unknown>) => authSearchSchema.parse(search);

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: LoginPage,
});
const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login/account-not-found",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: AccountNotFoundPage,
});
const forgotRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login/forgot",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: ForgotPasswordPage,
});
const signupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/signup",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: SignupPage,
});
const callbackRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/callback",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: CallbackPage,
});
const verifyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account/verify-email",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: VerifyEmailPage,
});
const passwordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account/password",
  validateSearch: authSearch,
  // Open without a session also in an organization's installation (InstallationGate).
  staticData: { withoutSession: true },
  component: SetPasswordPage,
});
const devicesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account/devices",
  component: DevicesPage,
});

const authRoutes = [
  loginRoute,
  notFoundRoute,
  forgotRoute,
  signupRoute,
  callbackRoute,
  verifyRoute,
  passwordRoute,
  devicesRoute,
] as const;

export const routeTree = rootRoute.addChildren([
  ...authRoutes,
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
  interface StaticDataRouteOption {
    /** The screen opens without a session in an organization's installation (signing in, links from emails). */
    withoutSession?: boolean;
  }
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
