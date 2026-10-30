import { useLocation, useMatches, useNavigate } from "@tanstack/react-router";
import { type ReactNode, useEffect, useRef } from "react";
import { useAuthMethods } from "@/api/auth";
import { useSessionState } from "@/lib/auth/tokens";

/**
 * Shows its content only with a session; without one, sends to the sign in and comes back here
 * afterwards (`return_to`). While a stored session is being restored it shows nothing.
 */
export function RequireSession({ children }: { children: ReactNode }) {
  const { ready, claims, hasRefreshToken } = useSessionState();
  const location = useLocation();
  const navigate = useNavigate();
  // Path the redirect was started from: one navigation per path, even if this stays mounted.
  const leaving = useRef<string | null>(null);
  const signedOut = ready && !claims && !hasRefreshToken;

  useEffect(() => {
    // Navigate once per path: re-rendering while the navigation is pending must not start another one,
    // but landing on another path while still signed out (e.g. after signing out) must.
    const here = `${location.pathname}${location.searchStr ?? ""}`;
    if (!signedOut || leaving.current === here || location.pathname.startsWith("/login")) return;
    leaving.current = here;
    navigate({
      to: "/login",
      search: { return_to: here },
      replace: true,
    });
  }, [signedOut, navigate, location.pathname, location.searchStr]);

  if (claims) return <>{children}</>;
  return <div aria-busy="true" className="min-h-[50vh]" />;
}

/**
 * Closes an organization's installation: every screen needs a session, including the ones defined
 * in the future, except those whose route says `staticData: { withoutSession: true }` (signing in
 * and the links that arrive by email). Without a session it goes to the sign in and, afterwards,
 * back to where the person was. On the main platform each route decides.
 */
export function InstallationGate({ children }: { children: ReactNode }) {
  const methods = useAuthMethods();
  const open = useMatches({ select: (matches) => matches.some((m) => m.staticData.withoutSession) });
  if (open) return <>{children}</>;
  if (methods.isPending) return <div aria-busy="true" className="min-h-[50vh]" />;
  // Without the methods the screen still opens: in an organization the backend answers 401.
  if (!methods.data?.organization_name) return <>{children}</>;
  return <RequireSession>{children}</RequireSession>;
}
