import { useNavigate, useSearch } from "@tanstack/react-router";
import { Plane } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import {
  type AuthMethods,
  authorizeWithProvider,
  isLoginFailed,
  loginWithPassword,
  lookupEmail,
  useAuthMethods,
} from "@/api/auth";
import { useTrip } from "@/features/trip/public";
import { checkoutItemKey, comesFromCheckout, rememberProviderSignIn, safeReturnTo } from "@/lib/auth/flow";
import { acknowledgeSessionEnd, useSessionState } from "@/lib/auth/tokens";
import { formatMoney, formatShortDate } from "@/lib/format";
import {
  AuthLayout,
  EmailPill,
  ErrorBox,
  Field,
  Heading,
  OrDivider,
  PrimaryButton,
  ProviderButton,
  SessionEndedBox,
  TextLink,
} from "./ui";

/** The one message of a failed sign in: it never says why (03-usuarios-y-acceso.md §8.1). */
export const LOGIN_FAILED = "No pudimos iniciar sesión.";

/** Summary of the flight being booked, when the sign in comes from the checkout. */
function TripBanner({ itemKey }: { itemKey: string }) {
  const item = useTrip((state) => state.items[itemKey]);
  if (!item) return null;
  const first = item.flight.slices[0];
  const last = item.flight.slices[item.flight.slices.length - 1];
  const departure = first?.segments[0]?.departing_at;
  const route = first && last ? `${first.origin.code} → ${first.destination.code}` : "";
  return (
    <div className="flex items-center gap-3 rounded-[10px] bg-canvas px-3.5 py-3">
      <span
        aria-hidden
        className="inline-flex size-9 flex-none items-center justify-center rounded-lg bg-action-soft text-action"
      >
        <Plane className="size-[18px]" />
      </span>
      <span className="flex flex-col text-[13px] text-ink-2">
        <strong className="font-mono text-[14px] text-ink">
          {route}
          {departure ? ` · ${formatShortDate(departure.slice(0, 10))}` : ""} ·{" "}
          {formatMoney(item.fare.price.total)}
        </strong>
        Tu viaje queda guardado mientras ingresas.
      </span>
    </div>
  );
}

function ProviderButtons({
  methods,
  returnTo,
  disabled,
}: {
  methods: AuthMethods;
  returnTo: string | null;
  disabled: boolean;
}) {
  const [going, setGoing] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const start = async (slug: string, name: string) => {
    setGoing(slug);
    setFailed(false);
    try {
      const url = await authorizeWithProvider(slug, returnTo);
      rememberProviderSignIn(url, { provider: slug, providerName: name, returnTo });
      window.location.assign(url);
    } catch {
      setGoing(null);
      setFailed(true);
    }
  };
  return (
    <>
      {failed ? (
        <ErrorBox>
          <strong>{LOGIN_FAILED}</strong> Prueba de nuevo.
        </ErrorBox>
      ) : null}
      {methods.providers.map((provider) => (
        <ProviderButton
          key={provider.slug}
          name={provider.display_name}
          kind={provider.slug === "google" ? "google" : "sso"}
          label={provider.slug === "google" ? "Continuar con Google" : `Entrar con ${provider.display_name}`}
          loading={going === provider.slug}
          disabled={disabled || (going !== null && going !== provider.slug)}
          onClick={() => start(provider.slug, provider.display_name)}
        />
      ))}
      {going ? <p className="m-0 text-[13px] text-muted-2">Puede tardar unos segundos.</p> : null}
    </>
  );
}

/**
 * «Ingresa» (design boards "Ingreso · pantalla completa" and "Cuenta 1–2"): the methods of the
 * installation, the email in two steps and the password.
 */
export function LoginPage() {
  const search = useSearch({ strict: false }) as { return_to?: string; error?: string; email?: string };
  const navigate = useNavigate();
  const returnTo = safeReturnTo(search.return_to);
  const fromCheckout = comesFromCheckout(returnTo);
  const itemKey = checkoutItemKey(returnTo);
  const methods = useAuthMethods();
  const { ended } = useSessionState();
  const [sessionEnded] = useState(ended === "revoked" || ended === "expired" ? ended : null);
  const [step, setStep] = useState<"email" | "password">("email");
  const [email, setEmail] = useState(search.email ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(search.error === "provider");
  const [busy, setBusy] = useState(false);

  useEffect(() => acknowledgeSessionEnd(), []);

  const data = methods.data;
  const organization = data?.organization_name ?? null;
  const goBack = () => navigate({ to: returnTo ?? "/" });

  const submitEmail = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(false);
    try {
      const result = await lookupEmail(email);
      if (result.exists) setStep("password");
      else navigate({ to: "/login/account-not-found", search: { email, return_to: returnTo ?? undefined } });
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  const submitPassword = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(false);
    try {
      await loginWithPassword(email, password);
      goBack();
    } catch (failure) {
      setError(isLoginFailed(failure) || true);
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  const title =
    step === "password"
      ? "Ingresa tu contraseña"
      : fromCheckout
        ? "Ingresa para reservar"
        : "Te damos la bienvenida";
  const subtitle =
    step === "password"
      ? "Es la de tu cuenta de Vuelos."
      : organization
        ? `Usa la cuenta que te dio ${organization}.`
        : "Usa tu cuenta de Google o tu email.";

  return (
    <AuthLayout
      organizationName={organization}
      topLink={
        data?.signup_enabled ? (
          <span>
            ¿Primera vez?{" "}
            <TextLink to="/signup" search={{ return_to: returnTo ?? undefined }}>
              Crea tu cuenta
            </TextLink>
          </span>
        ) : null
      }
    >
      {fromCheckout && itemKey ? <TripBanner itemKey={itemKey} /> : null}
      {sessionEnded ? <SessionEndedBox reason={sessionEnded} /> : null}
      <Heading title={title} subtitle={subtitle} />

      {step === "email" ? (
        <div className="flex flex-col gap-3.5">
          {error && !data?.password_enabled ? (
            <ErrorBox>
              <strong>{LOGIN_FAILED}</strong> Prueba de nuevo.
            </ErrorBox>
          ) : null}
          {data ? <ProviderButtons methods={data} returnTo={returnTo} disabled={busy} /> : null}
          {data?.password_enabled ? (
            <form onSubmit={submitEmail} className="flex flex-col gap-3.5" noValidate>
              {data.providers.length > 0 ? <OrDivider /> : null}
              {error ? (
                <ErrorBox>
                  <strong>{LOGIN_FAILED}</strong> Prueba de nuevo.
                </ErrorBox>
              ) : null}
              <Field
                label="Email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <PrimaryButton disabled={busy}>Continuar</PrimaryButton>
            </form>
          ) : null}
          {data && !data.password_enabled ? (
            <p className="m-0 text-[13px] text-muted-2">
              ¿Problemas para entrar? Habla con quien administra los viajes en tu empresa.
            </p>
          ) : null}
        </div>
      ) : (
        <form onSubmit={submitPassword} className="flex flex-col gap-3.5" noValidate>
          <EmailPill email={email} onChange={() => setStep("email")} />
          {error ? (
            <ErrorBox>
              <strong>{LOGIN_FAILED}</strong>
            </ErrorBox>
          ) : null}
          <PasswordField value={password} onChange={setPassword} invalid={error} />
          <PrimaryButton disabled={busy}>Ingresar</PrimaryButton>
          <span className="self-center p-2 text-[14px]">
            <TextLink to="/login/forgot" search={{ email, return_to: returnTo ?? undefined }}>
              ¿Olvidaste tu contraseña?
            </TextLink>
          </span>
        </form>
      )}

      <p className="m-0 hidden text-center text-[13px] text-muted-2 md:block">
        {organization
          ? "¿No tienes acceso? Pídeselo a quien administra los viajes en tu empresa."
          : "Buscar vuelos no requiere cuenta; la pedimos para reservar."}
      </p>
    </AuthLayout>
  );
}

/** Password with «Mostrar» / «Ocultar». */
export function PasswordField({
  value,
  onChange,
  invalid,
  label = "Contraseña",
  autoComplete = "current-password",
  describedBy,
}: {
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
  label?: string;
  autoComplete?: string;
  describedBy?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <label className="flex flex-col gap-2 font-semibold text-[14px]">
      {label}
      <span className="relative block">
        <input
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`box-border h-[52px] w-full rounded-[10px] border pr-[76px] pl-3.5 font-normal text-[16px] outline-none focus:border-2 focus:pl-[13px] focus:shadow-[0_0_0_4px_var(--color-action-soft)] ${
            invalid ? "border-2 border-bad-strong pl-[13px]" : "border-line-dash focus:border-action"
          }`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute top-2 right-2 h-9 cursor-pointer border-0 bg-transparent px-2.5 font-semibold text-[14px] text-action"
        >
          {visible ? "Ocultar" : "Mostrar"}
        </button>
      </span>
    </label>
  );
}
