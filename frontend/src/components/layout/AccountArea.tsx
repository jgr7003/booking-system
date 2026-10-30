import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { Info, Menu, X } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useState } from "react";
import { signOut, useAuthMethods } from "@/api/auth";
import { dismissNotice, firstName, initials, pendingNotice } from "@/lib/auth/flow";
import { useSessionState } from "@/lib/auth/tokens";

/**
 * Right side of the dark bar (design board "Cuenta 6–7"): «Mis reservas · pronto» and «Ingresar»
 * without a session, or the account button and its menu. Below 720 px they move into the ☰ menu.
 */
export function AccountArea() {
  const { claims, ready, hasRefreshToken } = useSessionState();
  const methods = useAuthMethods();
  const organization = methods.data?.organization_name ?? null;
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const returnTo = `${location.pathname}${location.searchStr ?? ""}`;
  const signingIn = !ready || (hasRefreshToken && !claims);

  const leave = async () => {
    setOpen(false);
    await signOut();
    // An organization's installation is closed without a session: back to its sign in.
    navigate({ to: organization ? "/login" : "/" });
  };

  const soon = (
    <span
      aria-disabled="true"
      className="inline-flex items-center gap-1.5 whitespace-nowrap text-[14px] text-line-strong"
    >
      Mis reservas
      <span className="rounded border border-muted-2 px-[5px] py-px font-semibold text-[10px]">PRONTO</span>
    </span>
  );

  const signIn = (
    <Link
      to="/login"
      search={{ return_to: returnTo }}
      className="inline-flex h-9 items-center whitespace-nowrap rounded-md border border-muted-2 px-3.5 font-semibold text-[14px] text-white no-underline hover:text-white"
    >
      Ingresar
    </Link>
  );

  const menuItems = claims ? (
    <>
      <div className="flex items-center gap-3 border-line-soft border-b px-4 py-3.5">
        <span className="inline-flex size-10 flex-none items-center justify-center rounded-full bg-action font-mono font-semibold text-white">
          {initials(claims.name)}
        </span>
        <span className="flex min-w-0 flex-col">
          <strong className="text-[15px]">{claims.name}</strong>
          <span className="truncate text-[13px] text-muted">{claims.email}</span>
          {organization ? (
            <span className="font-semibold text-[12px] text-action-hover">{organization}</span>
          ) : null}
        </span>
      </div>
      <DropdownMenu.Item
        disabled
        className="flex items-center justify-between px-4 py-3 text-[14px] text-muted outline-none"
      >
        Mis reservas
        <span className="rounded bg-action-soft px-1.5 py-0.5 font-semibold text-[10px] text-action-hover tracking-[0.04em]">
          PRÓXIMAMENTE
        </span>
      </DropdownMenu.Item>
      <DropdownMenu.Item asChild>
        <Link
          to="/account/devices"
          className="block px-4 py-3 text-[14px] text-ink no-underline outline-none hover:bg-canvas focus:bg-canvas"
        >
          Dispositivos conectados
        </Link>
      </DropdownMenu.Item>
      <DropdownMenu.Item
        onSelect={leave}
        className="block cursor-pointer border-line-soft border-t px-4 py-3 text-[14px] text-bad outline-none hover:bg-canvas focus:bg-canvas"
      >
        Cerrar sesión
      </DropdownMenu.Item>
    </>
  ) : null;

  return (
    <>
      {organization ? (
        <span className="whitespace-nowrap border-header-line border-l pl-3.5 text-[14px] text-line-strong">
          {organization}
        </span>
      ) : null}
      <span className="flex-1" />
      <div className="hidden items-center gap-4 min-[720px]:flex">
        {soon}
        {claims ? (
          <DropdownMenu.Root open={open} onOpenChange={setOpen}>
            <DropdownMenu.Trigger className="inline-flex h-10 cursor-pointer items-center gap-2 whitespace-nowrap rounded-[20px] border border-header-line bg-[#1F2937] py-0 pr-2 pl-1 text-[14px] text-white">
              <span className="inline-flex size-8 items-center justify-center rounded-full bg-action font-mono font-semibold text-[13px]">
                {initials(claims.name)}
              </span>
              {firstName(claims.name)}
              <span aria-hidden>▾</span>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="end"
                sideOffset={4}
                aria-label="Cuenta"
                className="z-50 w-[300px] overflow-hidden rounded-lg border border-line bg-white text-ink shadow-[0_12px_32px_rgba(17,24,39,0.18)]"
              >
                {menuItems}
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        ) : signingIn ? null : (
          signIn
        )}
      </div>
      <MobileMenu
        signedIn={Boolean(claims)}
        signIn={signIn}
        soon={soon}
        onLeave={leave}
        name={claims?.name}
      />
    </>
  );
}

/** The ☰ menu of narrow screens: opens as a panel above the page. */
function MobileMenu({
  signedIn,
  signIn,
  soon,
  onLeave,
  name,
}: {
  signedIn: boolean;
  signIn: React.ReactNode;
  soon: React.ReactNode;
  onLeave: () => void;
  name?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-[720px]:hidden">
      <button
        type="button"
        aria-label={open ? "Cerrar menú" : "Abrir menú"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex size-10 cursor-pointer items-center justify-center rounded-md border border-header-line bg-transparent text-white"
      >
        {open ? <X className="size-5" /> : <Menu className="size-5" />}
      </button>
      {open ? (
        <div className="absolute inset-x-0 top-full z-50 flex flex-col gap-3 bg-ink px-4 pt-2 pb-4 shadow-lg">
          {soon}
          {signedIn ? (
            <>
              <span className="text-[14px] text-line-strong">{name}</span>
              <Link
                to="/account/devices"
                className="text-[14px] text-white no-underline"
                onClick={() => setOpen(false)}
              >
                Dispositivos conectados
              </Link>
              <button
                type="button"
                onClick={onLeave}
                className="cursor-pointer self-start border-0 bg-transparent p-0 text-[14px] text-[#F3B8B2]"
              >
                Cerrar sesión
              </button>
            </>
          ) : (
            signIn
          )}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Blue notice after creating the account with a provider (design board "Cuenta 6–7"): it can be
 * closed and doesn't block anything.
 */
export function PasswordEmailNotice() {
  const [provider, setProvider] = useState(() => pendingNotice());
  if (!provider) return null;
  return (
    <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-5">
      <div
        role="status"
        className="mt-4 flex items-center gap-3 rounded-lg border border-action-ring bg-action-soft px-4 py-3 text-[14px] text-action-hover"
      >
        <Info aria-hidden className="size-[18px] flex-none" />
        <span className="flex-1">
          Te enviamos un correo para que crees una contraseña. Mientras tanto, sigue entrando con {provider}.
        </span>
        <button
          type="button"
          aria-label="Cerrar aviso"
          onClick={() => {
            dismissNotice();
            setProvider(null);
          }}
          className="inline-flex size-9 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent text-[18px] text-action-hover"
        >
          ×
        </button>
      </div>
    </div>
  );
}
