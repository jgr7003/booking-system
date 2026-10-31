import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { finishProviderSignIn } from "@/api/auth";
import { safeReturnTo, takeProviderSignIn } from "@/lib/auth/flow";
import { AuthLayout, Heading } from "./ui";

/**
 * Where the provider sends the browser back (`/auth/callback?code&state`). It finishes the sign in
 * with the device's DPoP proof and goes back to where it started, or to «No encontramos tu cuenta».
 * Any failure goes back to the sign in with the one error message.
 */
export function CallbackPage() {
  const search = useSearch({ strict: false }) as { code?: string; state?: string; error?: string };
  const navigate = useNavigate();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const pending = search.state ? takeProviderSignIn(search.state) : null;
    const returnTo = pending?.returnTo ?? undefined;
    const failed = () =>
      navigate({ to: "/login", search: { error: "provider", return_to: returnTo }, replace: true });
    if (!pending || !search.code || !search.state || search.error) {
      failed();
      return;
    }
    finishProviderSignIn(pending.provider, search.code, search.state)
      .then((result) => {
        if (result.status === "signed_in") {
          navigate({ to: safeReturnTo(result.tokens.return_to) ?? pending.returnTo ?? "/", replace: true });
        } else {
          navigate({
            to: "/login/account-not-found",
            search: {
              attempt: result.attempt_id,
              provider: pending.provider,
              provider_name: pending.providerName,
              return_to: returnTo,
            },
            replace: true,
          });
        }
      })
      .catch(failed);
  }, [search, navigate]);

  return (
    <AuthLayout>
      <div role="status" aria-busy="true" className="flex flex-col gap-3">
        <Heading title="Ingresando…" subtitle="Un momento." />
      </div>
    </AuthLayout>
  );
}
