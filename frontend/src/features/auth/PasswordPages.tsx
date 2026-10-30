import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Info } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { forgotPassword, setPassword, useAuthMethods, usePasswordLink, verifyEmail } from "@/api/auth";
import { safeReturnTo, takeReturnTo } from "@/lib/auth/flow";
import { useSessionState } from "@/lib/auth/tokens";
import { PasswordField } from "./LoginPage";
import { MIN_PASSWORD } from "./SignupPage";
import {
  AuthLayout,
  ErrorBox,
  Field,
  Heading,
  PasswordRequirement,
  PrimaryButton,
  StatusIcon,
  TextLink,
} from "./ui";

const primaryLink =
  "flex h-[52px] items-center justify-center rounded-[10px] bg-action font-semibold text-[16px] text-white no-underline shadow-[0_6px_16px_rgba(29,78,216,0.28)] hover:bg-action-hover hover:text-white";

/** «¿Olvidaste tu contraseña?» and «Revisa tu correo» (design board "Cuenta 2"). */
export function ForgotPasswordPage() {
  const search = useSearch({ strict: false }) as { email?: string; return_to?: string };
  const returnTo = safeReturnTo(search.return_to);
  const methods = useAuthMethods();
  const [email, setEmail] = useState(search.email ?? "");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFailed(false);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout organizationName={methods.data?.organization_name}>
      {sent ? (
        <div role="status" className="flex flex-col gap-[18px]">
          <StatusIcon kind="mail" />
          <Heading
            title="Revisa tu correo"
            subtitle={
              <>
                Si <strong className="text-ink">{email}</strong> tiene una cuenta, te enviamos un enlace.
              </>
            }
          />
          <p className="m-0 text-[14px] text-muted">
            ¿No llegó? Revisa la carpeta de spam o{" "}
            <button
              type="button"
              onClick={() => setSent(false)}
              className="cursor-pointer border-0 bg-transparent p-0 text-[14px] text-action underline"
            >
              prueba con otro email
            </button>
            .
          </p>
          <span className="text-[14px]">
            <TextLink to="/login" search={{ email, return_to: returnTo ?? undefined }}>
              Volver a ingresar
            </TextLink>
          </span>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-[18px]" noValidate>
          <span className="text-[14px]">
            <Link to="/login" search={{ email, return_to: returnTo ?? undefined }}>
              ← Volver
            </Link>
          </span>
          <Heading
            title="Elige una contraseña nueva"
            subtitle="Escribe el email de tu cuenta y te enviamos un enlace. Sirve también si todavía no creaste una contraseña."
          />
          {failed ? (
            <ErrorBox>Ya te enviamos varios correos. Espera unos minutos y prueba de nuevo.</ErrorBox>
          ) : null}
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <PrimaryButton disabled={busy || !email.includes("@")}>Enviarme el enlace</PrimaryButton>
        </form>
      )}
    </AuthLayout>
  );
}

/** «Este enlace ya no sirve», with «Enviarme otro». */
function ExpiredLink({ email: initial }: { email?: string }) {
  const [email, setEmail] = useState(initial ?? "");
  const [sent, setSent] = useState(false);
  const send = async (event: FormEvent) => {
    event.preventDefault();
    await forgotPassword(email).catch(() => undefined);
    setSent(true);
  };
  if (sent) {
    return (
      <div role="status" className="flex flex-col gap-[18px]">
        <StatusIcon kind="mail" />
        <Heading
          title="Revisa tu correo"
          subtitle={
            <>
              Si <strong className="text-ink">{email}</strong> tiene una cuenta, te enviamos un enlace nuevo.
            </>
          }
        />
      </div>
    );
  }
  return (
    <form onSubmit={send} className="flex flex-col gap-[18px]" noValidate>
      <StatusIcon kind="error" />
      <Heading
        title="Este enlace ya no sirve"
        subtitle="Venció o ya lo usaste. Pide otro y abre el más reciente."
      />
      <Field
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <PrimaryButton disabled={!email.includes("@")}>Enviarme otro</PrimaryButton>
    </form>
  );
}

/** «Crea tu contraseña» / «Elige una contraseña nueva», from the email (design board "Cuenta 5"). */
export function SetPasswordPage() {
  const search = useSearch({ strict: false }) as { token?: string };
  const token = search.token ?? "";
  const methods = useAuthMethods();
  const link = usePasswordLink(token);
  // Opened from the email, often on a device without a session: then it goes on to sign in.
  const { claims } = useSessionState();
  const signedIn = claims !== null;
  const [password, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [failed, setFailed] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFailed(false);
    try {
      await setPassword(token, password);
      setDone(true);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const info = link.data;
  const creating = info?.kind === "set";
  const via = info?.signs_in_with;

  let content: React.ReactNode;
  if (!token || link.isError || (failed && !info)) {
    content = <ExpiredLink />;
  } else if (!info) {
    content = <p className="m-0 text-[15px] text-muted">Cargando…</p>;
  } else if (done) {
    content = (
      <div role="status" className="flex flex-col gap-[18px]">
        <StatusIcon kind="ok" />
        {creating ? (
          <Heading
            title="Listo, ya tienes contraseña"
            subtitle={`Desde ahora puedes entrar con tu email y contraseña${via ? `, o con ${via}, como prefieras` : ""}.`}
          />
        ) : (
          <Heading
            title="Cambiaste tu contraseña"
            subtitle="Cerramos la sesión en todos tus dispositivos. Ingresa con tu contraseña nueva."
          />
        )}
        {creating && signedIn ? (
          <Link to="/" className={primaryLink}>
            Seguir
          </Link>
        ) : (
          <Link to="/login" search={{ email: info.email }} className={primaryLink}>
            Ingresar
          </Link>
        )}
      </div>
    );
  } else {
    content = (
      <form onSubmit={submit} className="flex flex-col gap-[18px]" noValidate>
        <Heading
          title={creating ? "Crea tu contraseña" : "Elige una contraseña nueva"}
          subtitle={
            <>
              Para <strong className="text-ink">{info.email}</strong>.
              {creating && via ? ` Vas a poder seguir entrando también con ${via}.` : null}
            </>
          }
        />
        {!creating ? (
          <div className="flex items-start gap-2.5 rounded-md border border-action-ring bg-action-soft p-3 text-[14px] text-action-hover">
            <Info aria-hidden className="mt-px size-[18px] flex-none" />
            <span>Al guardarla, se cierra la sesión en todos tus dispositivos.</span>
          </div>
        ) : null}
        {failed ? <ErrorBox>No pudimos guardar la contraseña. Prueba de nuevo.</ErrorBox> : null}
        <PasswordField
          label="Contraseña nueva"
          autoComplete="new-password"
          value={password}
          onChange={setValue}
          describedBy="new-password-requirement"
        />
        <PasswordRequirement id="new-password-requirement" length={password.length} min={MIN_PASSWORD} />
        <PrimaryButton disabled={busy || password.length < MIN_PASSWORD}>Guardar contraseña</PrimaryButton>
        {creating && via ? (
          <span className="self-center text-[14px]">
            <TextLink to={signedIn ? "/" : "/login"} search={signedIn ? undefined : { email: info.email }}>
              Ahora no, seguir con {via.startsWith("el SSO") ? "el SSO" : via}
            </TextLink>
          </span>
        ) : null}
      </form>
    );
  }

  return <AuthLayout organizationName={methods.data?.organization_name}>{content}</AuthLayout>;
}

/** Opens the verification link: verifies the email, signs this device in and goes back to the trip. */
export function VerifyEmailPage() {
  const search = useSearch({ strict: false }) as { token?: string };
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!search.token) {
      setFailed(true);
      return;
    }
    verifyEmail(search.token)
      .then(() => navigate({ to: takeReturnTo() ?? "/", replace: true }))
      .catch(() => setFailed(true));
  }, [search.token, navigate]);

  return (
    <AuthLayout variant="signup" mobileTitle>
      {failed ? (
        <ExpiredLink />
      ) : (
        <div role="status" aria-busy="true" className="flex flex-col gap-[18px]">
          <StatusIcon kind="mail" />
          <Heading title="Verificando tu email…" subtitle="Un momento: enseguida vuelves a tu viaje." />
        </div>
      )}
    </AuthLayout>
  );
}
