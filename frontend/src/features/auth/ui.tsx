import { Link } from "@tanstack/react-router";
import { Check, CircleAlert, Clock, KeyRound, Lock, Mail } from "lucide-react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { LogoIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

/**
 * Pieces of the account screens (design boards "Ingreso / Crear cuenta · pantalla completa",
 * "Cuenta 1–5" and their mobile versions, Propuesta A v3).
 */

const PANEL_TEXT = {
  login: {
    title: "Tus viajes de trabajo, en un solo lugar.",
    points: [
      "Compara varias aerolíneas en una sola búsqueda.",
      "Arma tu viaje con vuelos y, pronto, hotel.",
      "Tu código de reserva y tus tickets, siempre a mano.",
    ],
  },
  signup: {
    title: "Crea tu cuenta y reserva en minutos.",
    points: [
      "Tus datos de pasajero quedan listos para la próxima.",
      "Ves qué incluye cada tarifa antes de pagar.",
      "Recibes la confirmación y los tickets por correo.",
    ],
  },
} as const;

// Photos of the visual panel: every `.webp` in `src/assets/login/` (03-usuarios-y-acceso.md §21).
const BACKGROUNDS = Object.values(
  import.meta.glob<string>("/src/assets/login/*.webp", { eager: true, import: "default", query: "?url" }),
);

// One at random per page load, the same on every account screen while the page is open.
const background = BACKGROUNDS[Math.floor(Math.random() * BACKGROUNDS.length)];

/** The floating card over the photo: a confirmed booking (sign in) or «Tu viaje» (sign up). */
function FloatingCard({ variant }: { variant: "login" | "signup" }) {
  if (variant === "signup") {
    return (
      <div
        aria-hidden
        className="absolute top-[8%] right-[4%] flex w-[220px] animate-float flex-col gap-2 rounded-xl bg-white px-4 py-3.5 text-ink shadow-[0_18px_40px_rgba(0,0,0,0.35)]"
      >
        <span className="font-semibold text-[12px] text-muted uppercase tracking-[0.06em]">Tu viaje</span>
        <span className="flex justify-between text-[13px]">
          <span>✈ Vuelo LHR → JFK</span>
          <strong className="font-mono">524,44</strong>
        </span>
        <span className="flex justify-between text-[13px] text-muted-2">
          <span>+ Hotel</span>
          <span>pronto</span>
        </span>
      </div>
    );
  }
  return (
    <div
      aria-hidden
      className="absolute top-[6%] left-[4%] flex w-[230px] animate-float flex-col gap-1.5 rounded-xl bg-white px-4 py-3.5 text-ink shadow-[0_18px_40px_rgba(0,0,0,0.35)]"
    >
      <span className="flex items-center gap-1.5 font-semibold text-[12px] text-ok">
        <span className="inline-flex size-4 items-center justify-center rounded-full bg-ok text-[10px] text-white">
          ✓
        </span>
        Reserva confirmada
      </span>
      <span className="font-mono font-semibold text-[18px]">BOG → CLO</span>
      <span className="text-[12px] text-muted">mar 10 nov · 06:58 · BA 1516</span>
      <span className="self-start rounded bg-action-soft px-1.5 py-[3px] font-mono font-semibold text-[12px] text-action-hover tracking-[0.1em]">
        GNA3VA
      </span>
    </div>
  );
}

/**
 * Full-screen layout of the account screens: the visual panel on the left (or on top, compact, on
 * mobile) and the form on the right.
 */
export function AuthLayout({
  variant = "login",
  organizationName,
  topLink,
  mobileTitle = false,
  children,
}: {
  variant?: "login" | "signup";
  organizationName?: string | null;
  /** Link at the top right, e.g. «¿Primera vez? Crea tu cuenta». */
  topLink?: ReactNode;
  /** On mobile, show the panel's title under the logo instead of the illustration (sign up). */
  mobileTitle?: boolean;
  children: ReactNode;
}) {
  const panel = PANEL_TEXT[variant];
  return (
    <div className="flex min-h-screen flex-col bg-white text-ink md:flex-row md:flex-wrap lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(480px,3fr)]">
      <aside
        aria-label="Vuelos para viajes de trabajo"
        className="relative hidden min-h-screen min-w-0 flex-[1_1_560px] flex-col gap-7 overflow-hidden bg-night px-12 py-10 text-white md:flex"
      >
        {background ? (
          <>
            <img
              src={background}
              alt=""
              className="absolute inset-0 size-full object-cover object-[70%_center]"
            />
            {/* Darker at the top and the bottom, where the brand and the text sit over the photo. */}
            <div
              aria-hidden
              className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(11,21,48,0.65)_0%,rgba(11,21,48,0.1)_25%,rgba(11,21,48,0.15)_55%,rgba(11,21,48,0.92)_100%)]"
            />
          </>
        ) : null}
        <div className="relative">
          <Brand organizationName={organizationName} />
        </div>
        <div className="relative flex-1">
          <FloatingCard variant={variant} />
        </div>
        <div className="relative flex flex-col gap-3.5">
          <h2 className="m-0 max-w-[460px] font-bold text-[34px] leading-[1.15] tracking-[-0.01em]">
            {panel.title}
          </h2>
          <ul className="m-0 flex list-none flex-col gap-2 p-0 text-[15px] text-action-ring">
            {panel.points.map((point) => (
              <li key={point} className="flex items-center gap-2.5">
                <span aria-hidden className="text-action-light">
                  ✓
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <div
        className={cn(
          "flex flex-col bg-night px-5 pt-[22px] text-white md:hidden",
          mobileTitle ? "gap-1.5 pb-[34px]" : "gap-2.5",
        )}
      >
        <span className="font-bold text-[17px]">✈ Vuelos</span>
        {mobileTitle ? (
          <span className="font-bold text-[20px] leading-[1.2]">{panel.title}</span>
        ) : background ? (
          <img
            src={background}
            alt=""
            className="block h-[180px] w-full rounded-t-[14px] object-cover object-[70%_30%]"
          />
        ) : null}
      </div>

      <main className="relative -mt-3.5 flex flex-[1_1_480px] flex-col rounded-t-[18px] bg-white px-5 py-[22px] md:mt-0 md:min-h-screen md:rounded-none md:px-10 md:py-8">
        <div className="hidden min-h-11 items-center justify-end text-[14px] text-ink-2 md:flex">
          {topLink}
        </div>
        <div className="flex flex-1 items-start justify-center md:items-center">
          <div className="flex w-full max-w-[400px] flex-col gap-[18px] md:gap-5">
            {children}
            {topLink ? <p className="m-0 text-center text-[14px] text-ink-2 md:hidden">{topLink}</p> : null}
          </div>
        </div>
      </main>
    </div>
  );
}

function Brand({ organizationName }: { organizationName?: string | null }) {
  return (
    <span className="flex items-center gap-3 font-bold text-[20px]">
      <LogoIcon />
      Vuelos
      {organizationName ? (
        <span className="border-night-line border-l pl-3 font-medium text-[15px] text-action-ring">
          Viajes de {organizationName}
        </span>
      ) : null}
    </span>
  );
}

export function Heading({ title, subtitle }: { title: string; subtitle?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="m-0 font-bold text-[26px] leading-[1.15] tracking-[-0.01em] md:text-[32px]">{title}</h1>
      {subtitle ? <p className="m-0 text-[16px] text-muted leading-[1.5]">{subtitle}</p> : null}
    </div>
  );
}

const buttonBase =
  "flex h-[52px] w-full cursor-pointer items-center justify-center gap-3 rounded-[10px] font-semibold text-[16px] disabled:cursor-not-allowed";

export function PrimaryButton({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="submit"
      className={cn(
        buttonBase,
        "border-0 bg-action text-white shadow-[0_6px_16px_rgba(29,78,216,0.28)] hover:bg-action-hover disabled:bg-line-soft disabled:text-muted-2 disabled:shadow-none",
        className,
      )}
      {...props}
    />
  );
}

export function SecondaryButton({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(buttonBase, "border border-line-dash bg-white text-ink hover:bg-surface-2", className)}
      {...props}
    />
  );
}

/** Spinner of a button that is taking the browser to a provider. */
function Spinner() {
  return (
    <span
      aria-hidden
      className="box-border size-4 animate-spin rounded-full border-2 border-action-pale border-t-action"
    />
  );
}

/** «G» monogram of the board. In production it should become Google's official button. */
function GoogleMark() {
  return (
    <span
      aria-hidden
      className="box-border inline-flex size-[22px] items-center justify-center rounded-full border-2 border-action font-bold text-[13px] text-action"
    >
      G
    </span>
  );
}

/**
 * Button of an identity provider: Google (gray border, «G») or an organization's SSO (dark border,
 * key). While the browser is being sent there it shows «Te llevamos a …» and the others are disabled.
 */
export function ProviderButton({
  name,
  kind,
  label,
  loading,
  disabled,
  onClick,
}: {
  name: string;
  kind: "google" | "sso";
  label: string;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        buttonBase,
        loading
          ? "border border-action bg-action-soft text-action-hover"
          : disabled
            ? "border border-line-soft bg-white text-subtle"
            : kind === "google"
              ? "border border-line-dash bg-white text-ink shadow-[0_1px_2px_rgba(17,24,39,0.06)] hover:bg-surface-2"
              : "border border-ink bg-white text-ink hover:bg-surface-2",
      )}
    >
      {loading ? (
        <Spinner />
      ) : kind === "google" ? (
        <GoogleMark />
      ) : (
        <KeyRound aria-hidden className="size-[18px]" />
      )}
      {loading ? `Te llevamos a ${name}…` : label}
    </button>
  );
}

export function OrDivider() {
  return (
    <div aria-hidden className="flex items-center gap-3 text-[13px] text-muted-2">
      <span className="h-px flex-1 bg-line-soft" />o con tu email
      <span className="h-px flex-1 bg-line-soft" />
    </div>
  );
}

export function Field({
  label,
  hint,
  invalid,
  className,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: ReactNode; invalid?: boolean }) {
  return (
    <label className="flex flex-col gap-2 font-semibold text-[14px]">
      {label}
      <input
        aria-invalid={invalid || undefined}
        className={cn(
          "box-border h-[52px] rounded-[10px] border border-line-dash bg-surface-2 px-3.5 font-normal text-[16px] outline-none focus:border-2 focus:border-action focus:bg-white focus:px-[13px] focus:shadow-[0_0_0_4px_var(--color-action-soft)] disabled:text-muted-2",
          invalid && "border-2 border-bad-strong px-[13px]",
          className,
        )}
        {...input}
      />
      {hint}
    </label>
  );
}

/** The email chosen in the first step, with «Cambiar» to go back to it. */
export function EmailPill({ email, onChange }: { email: string; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-full bg-canvas py-1.5 pr-1.5 pl-4 text-[15px]">
      <span className="truncate">{email}</span>
      <button
        type="button"
        onClick={onChange}
        className="h-9 cursor-pointer rounded-full border-0 bg-white px-3.5 font-semibold text-[14px] text-action"
      >
        Cambiar
      </button>
    </div>
  );
}

/** An email shown as fact («No encontramos…»), with the provider's mark if it came from one. */
export function EmailChip({ email, google }: { email: string; google?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 rounded-full bg-canvas px-3.5 py-2 text-[14px]">
      {google ? <GoogleMark /> : null}
      <strong className="truncate">{email}</strong>
    </div>
  );
}

/** Red box of an error, above the field (`role="alert"`). */
export function ErrorBox({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-[10px] border border-bad-line bg-bad-soft px-3 py-2.5 text-[14px] text-bad-ink-2"
    >
      <CircleAlert aria-hidden className="mt-px size-[18px] flex-none" />
      <span>{children}</span>
    </div>
  );
}

/** Notice of why the session ended (design board "Cuenta 9"): blue for security, gray for expiry. */
export function SessionEndedBox({ reason }: { reason: "revoked" | "expired" }) {
  const revoked = reason === "revoked";
  return (
    <div
      role="status"
      className={cn(
        "flex items-start gap-2.5 rounded-md border p-3 text-[14px]",
        revoked ? "border-action-ring bg-action-soft text-action-hover" : "border-line bg-canvas text-ink-2",
      )}
    >
      {revoked ? (
        <Lock aria-hidden className="mt-px size-[18px] flex-none" />
      ) : (
        <Clock aria-hidden className="mt-px size-[18px] flex-none" />
      )}
      <span>
        {revoked ? (
          <>
            <strong>Cerramos tu sesión por seguridad.</strong> Vuelve a ingresar.
          </>
        ) : (
          <>
            <strong>Tu sesión venció.</strong> Vuelve a ingresar. Tu viaje sigue guardado.
          </>
        )}
      </span>
    </div>
  );
}

/** Square icon at the top of a status screen («Revisa tu correo», «Listo»...). */
export function StatusIcon({ kind }: { kind: "mail" | "ok" | "error" }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-14 items-center justify-center rounded-2xl",
        kind === "mail" && "bg-action-soft text-action",
        kind === "ok" && "bg-ok-soft text-ok",
        kind === "error" && "bg-bad-soft text-bad",
      )}
    >
      {kind === "mail" ? (
        <Mail className="size-[26px]" />
      ) : kind === "ok" ? (
        <Check className="size-[26px]" />
      ) : null}
      {kind === "error" ? <CircleAlert className="size-[26px]" /> : null}
    </span>
  );
}

/** Live check of the password requirement: a bar and «○/✓ Al menos N caracteres». */
export function PasswordRequirement({ id, length, min }: { id: string; length: number; min: number }) {
  const ok = length >= min;
  return (
    <div id={id} aria-live="polite" className="-mt-1.5 flex items-center gap-2.5">
      <span aria-hidden className="flex h-1.5 flex-1 overflow-hidden rounded-[3px] bg-line-soft">
        <span
          className={cn("block h-1.5", ok ? "bg-ok" : "bg-action")}
          style={{ width: `${Math.min(100, Math.round((length / min) * 100))}%` }}
        />
      </span>
      <span className={cn("flex-none font-semibold text-[13px]", ok ? "text-ok" : "text-muted")}>
        {ok ? "✓" : "○"} Al menos {min} caracteres
      </span>
    </div>
  );
}

export function TextLink({
  to,
  search,
  children,
}: {
  to: string;
  search?: Record<string, unknown>;
  children: ReactNode;
}) {
  return (
    <Link to={to} search={search} className="font-semibold underline">
      {children}
    </Link>
  );
}
