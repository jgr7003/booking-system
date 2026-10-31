import { useSearch } from "@tanstack/react-router";
import { type FormEvent, useEffect, useState } from "react";
import { authorizeWithProvider, signUp, useAuthMethods } from "@/api/auth";
import { ApiError } from "@/api/client";
import { rememberProviderSignIn, rememberReturnTo, resendWait, safeReturnTo } from "@/lib/auth/flow";
import { formatRemaining } from "@/lib/format";
import { PasswordField } from "./LoginPage";
import {
  AuthLayout,
  ErrorBox,
  Field,
  Heading,
  OrDivider,
  PasswordRequirement,
  PrimaryButton,
  ProviderButton,
  StatusIcon,
  TextLink,
} from "./ui";

/** Shortest password the backend accepts (it keeps 10, not the 8 of the board). */
export const MIN_PASSWORD = 10;

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "user_already_exists") return "Ya hay una cuenta con ese email. Ingresa con ella.";
    if (error.code === "too_many_attempts") return "Ya te enviamos varios correos. Espera unos minutos.";
    if (error.code === "validation_error") return "Revisa los datos: el teléfono va con el código de país.";
  }
  return "No pudimos crear tu cuenta. Prueba de nuevo.";
}

/**
 * «Crea tu cuenta» for private travellers (design boards "Crear cuenta · pantalla completa" and
 * "Cuenta 4"), and «Revisa tu correo» with the resend countdown.
 */
export function SignupPage() {
  const search = useSearch({ strict: false }) as { email?: string; return_to?: string };
  const returnTo = safeReturnTo(search.return_to);
  const methods = useAuthMethods();
  const google = methods.data?.providers[0];
  const [name, setName] = useState("");
  const [email, setEmail] = useState(search.email ?? "");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [resends, setResends] = useState(0);
  const [waitUntil, setWaitUntil] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [going, setGoing] = useState(false);

  useEffect(() => {
    if (!sent) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [sent]);

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      await signUp({ email, display_name: name, password, phone_number: phone.trim() || null });
      rememberReturnTo(returnTo);
      setWaitUntil(Date.now() + resendWait(sent ? resends + 1 : 0) * 1000);
      if (sent) setResends((r) => r + 1);
      setSent(true);
      setNow(Date.now());
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      setError(
        `Completa tu nombre, tu email y una contraseña de al menos ${MIN_PASSWORD} caracteres, y acepta los términos.`,
      );
      return;
    }
    void send();
  };

  const withGoogle = async () => {
    if (!google) return;
    setGoing(true);
    try {
      const url = await authorizeWithProvider(google.slug, returnTo);
      rememberProviderSignIn(url, { provider: google.slug, providerName: google.display_name, returnTo });
      window.location.assign(url);
    } catch {
      setGoing(false);
      setError("No pudimos iniciar sesión. Prueba de nuevo.");
    }
  };

  const remaining = Math.max(0, waitUntil - now);
  const valid = name.trim().length > 0 && email.includes("@") && password.length >= MIN_PASSWORD && terms;

  return (
    <AuthLayout
      variant="signup"
      mobileTitle
      topLink={
        <span>
          ¿Ya tienes cuenta?{" "}
          <TextLink to="/login" search={{ return_to: returnTo ?? undefined }}>
            Ingresa
          </TextLink>
        </span>
      }
    >
      {sent ? (
        <div role="status" className="flex flex-col gap-[18px]">
          <StatusIcon kind="mail" />
          <Heading
            title="Revisa tu correo"
            subtitle={
              <>
                Te enviamos un enlace a <strong className="text-ink">{email}</strong> para confirmar tu email.
                {resends === 0 ? " Después vuelves directo a tu viaje." : null}
              </>
            }
          />
          {resends > 0 ? (
            <div className="flex items-center gap-2.5 rounded-md border border-ok-line bg-ok-soft px-3.5 py-2.5 text-[14px] text-ok-ink">
              <span aria-hidden>✓</span>Te lo reenviamos. Revisa también la carpeta de spam.
            </div>
          ) : null}
          {error ? <ErrorBox>{error}</ErrorBox> : null}
          <button
            type="button"
            onClick={send}
            disabled={busy || remaining > 0}
            className="h-[52px] cursor-pointer rounded-[10px] border border-line-soft bg-surface-2 font-semibold text-[16px] text-muted-2 enabled:border-line-dash enabled:bg-white enabled:text-ink disabled:cursor-not-allowed"
          >
            {remaining > 0 ? (
              <>
                Reenviar el correo en <span className="font-mono">{formatRemaining(remaining)}</span>
              </>
            ) : (
              "Reenviar el correo"
            )}
          </button>
          <button
            type="button"
            onClick={() => setSent(false)}
            className="h-11 cursor-pointer border-0 bg-transparent font-semibold text-[15px] text-action"
          >
            Cambiar email
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-[18px]" noValidate>
          <Heading title="Crea tu cuenta" subtitle="Gratis. Solo te pedimos lo necesario." />
          {google ? (
            <>
              <ProviderButton
                name={google.display_name}
                kind={google.slug === "google" ? "google" : "sso"}
                label={
                  google.slug === "google"
                    ? "Registrarme con Google"
                    : `Registrarme con ${google.display_name}`
                }
                loading={going}
                disabled={busy}
                onClick={withGoogle}
              />
              <OrDivider />
            </>
          ) : null}
          {error ? <ErrorBox>{error}</ErrorBox> : null}
          <Field
            label="Nombre y apellido"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Teléfono (opcional)"
            type="tel"
            autoComplete="tel"
            placeholder="+57 300 123 4567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <PasswordField
            label="Contraseña"
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
            describedBy="signup-password-requirement"
          />
          <PasswordRequirement id="signup-password-requirement" length={password.length} min={MIN_PASSWORD} />
          <label className="flex items-start gap-2.5 text-[14px] text-ink-2">
            <input
              type="checkbox"
              checked={terms}
              onChange={(e) => setTerms(e.target.checked)}
              className="mt-0.5 size-[18px] accent-action"
            />
            <span>
              Acepto los{" "}
              <a href="/terminos" className="underline">
                términos y condiciones
              </a>{" "}
              y la{" "}
              <a href="/privacidad" className="underline">
                política de privacidad
              </a>
              .
            </span>
          </label>
          <PrimaryButton disabled={busy}>Crear cuenta</PrimaryButton>
        </form>
      )}
    </AuthLayout>
  );
}
