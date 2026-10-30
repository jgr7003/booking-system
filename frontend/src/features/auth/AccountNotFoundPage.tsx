import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import {
  authorizeWithProvider,
  createPendingAccount,
  discardPendingSignup,
  getPendingSignup,
  useAuthMethods,
} from "@/api/auth";
import { noticePasswordEmail, rememberProviderSignIn, safeReturnTo } from "@/lib/auth/flow";
import { LOGIN_FAILED } from "./LoginPage";
import { AuthLayout, EmailChip, ErrorBox, Field, Heading, PrimaryButton, SecondaryButton } from "./ui";

const primaryLink =
  "flex h-[52px] items-center justify-center rounded-[10px] bg-action font-semibold text-[16px] text-white no-underline shadow-[0_6px_16px_rgba(29,78,216,0.28)] hover:bg-action-hover hover:text-white";

/**
 * «No encontramos una cuenta con este email» (design board "Cuenta 3"): after a provider sign in
 * (`attempt`) or after typing an email (`email`). Private travellers can create the account;
 * in an organization, it must give access first.
 */
export function AccountNotFoundPage() {
  const search = useSearch({ strict: false }) as {
    attempt?: string;
    email?: string;
    provider?: string;
    provider_name?: string;
    return_to?: string;
  };
  const navigate = useNavigate();
  const returnTo = safeReturnTo(search.return_to);
  const methods = useAuthMethods();
  const organization = methods.data?.organization_name ?? null;
  const fromProvider = Boolean(search.attempt);
  const pending = useQuery({
    queryKey: ["auth", "pending", search.attempt],
    queryFn: () => getPendingSignup(search.attempt as string),
    enabled: fromProvider,
    retry: false,
  });
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const email = fromProvider ? (pending.data?.email ?? "") : (search.email ?? "");
  const canCreate = fromProvider ? Boolean(pending.data?.can_create) : Boolean(methods.data?.signup_enabled);
  const providerName = search.provider_name ?? "tu cuenta";

  const create = async () => {
    if (!search.attempt) return;
    setBusy(true);
    setFailed(false);
    try {
      const tokens = await createPendingAccount(search.attempt, phone.trim() || null);
      noticePasswordEmail(providerName);
      navigate({ to: safeReturnTo(tokens.return_to) ?? returnTo ?? "/" });
    } catch {
      setFailed(true);
      setBusy(false);
    }
  };

  const anotherAccount = async () => {
    setBusy(true);
    if (search.attempt) await discardPendingSignup(search.attempt).catch(() => undefined);
    if (fromProvider && search.provider) {
      try {
        const url = await authorizeWithProvider(search.provider, returnTo, true);
        rememberProviderSignIn(url, { provider: search.provider, providerName, returnTo });
        window.location.assign(url);
        return;
      } catch {
        // Back to the sign in, which shows every method again.
      }
    }
    navigate({ to: "/login", search: { return_to: returnTo ?? undefined } });
  };

  const expired = fromProvider && pending.isError;

  return (
    <AuthLayout variant="signup" organizationName={organization} mobileTitle={!organization}>
      <Heading
        title={
          organization
            ? `No encontramos tu cuenta en ${organization}`
            : "No encontramos una cuenta con este email"
        }
      />
      {email ? <EmailChip email={email} google={search.provider === "google"} /> : null}
      {expired || failed ? (
        <ErrorBox>
          <strong>{LOGIN_FAILED}</strong> Prueba de nuevo.
        </ErrorBox>
      ) : null}
      <p className="m-0 text-[15px] text-ink-2 leading-[1.5]">
        {organization
          ? "Tu empresa todavía no te dio acceso. Pídeselo a quien administra los viajes en tu empresa. Si entraste con otra cuenta por error, prueba de nuevo."
          : fromProvider
            ? `Puede que sea tu primera vez, o que hayas elegido otra cuenta de ${providerName}. Si es la correcta, creamos tu cuenta con estos datos.`
            : "Revisa que esté bien escrito. Si es tu primera vez, crea una cuenta: lleva un minuto."}
      </p>
      {canCreate && fromProvider && !expired ? (
        <>
          <Field
            label="Teléfono (opcional)"
            type="tel"
            autoComplete="tel"
            placeholder="+57 300 123 4567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <PrimaryButton type="button" onClick={create} disabled={busy}>
            Crear cuenta
          </PrimaryButton>
        </>
      ) : null}
      {canCreate && !fromProvider ? (
        <Link to="/signup" search={{ email, return_to: returnTo ?? undefined }} className={primaryLink}>
          Crear cuenta
        </Link>
      ) : null}
      <SecondaryButton onClick={anotherAccount} disabled={busy}>
        {fromProvider || organization ? "Usar otra cuenta" : "Probar con otro email"}
      </SecondaryButton>
    </AuthLayout>
  );
}
