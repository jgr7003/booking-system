import { AppWindow, Monitor, Smartphone } from "lucide-react";
import { useState } from "react";
import {
  type DeviceSession,
  useCloseDeviceSession,
  useCloseOtherSessions,
  useDeviceSessions,
} from "@/api/auth";
import { RequireSession } from "@/components/layout/RequireSession";
import { TopBar } from "@/components/layout/TopBar";
import { deviceKind, lastUse, signedInOn } from "./logic";

function DeviceIcon({ name }: { name: string }) {
  const kind = deviceKind(name);
  const label = kind === "phone" ? "Celular" : kind === "app" ? "App" : "Computador";
  return (
    <span
      role="img"
      aria-label={label}
      className="inline-flex size-11 items-center justify-center rounded-lg bg-canvas text-ink-2"
    >
      {kind === "phone" ? (
        <Smartphone className="size-5" />
      ) : kind === "app" ? (
        <AppWindow className="size-5" />
      ) : (
        <Monitor className="size-5" />
      )}
    </span>
  );
}

function DeviceRow({ device, onClosed }: { device: DeviceSession; onClosed: (name: string) => void }) {
  const [asking, setAsking] = useState(false);
  const close = useCloseDeviceSession();
  return (
    <li className="border-line-soft border-t first:border-t-0">
      <div className="grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-4 px-5 py-4">
        <DeviceIcon name={device.device_name} />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <strong className="text-[16px]">{device.device_name}</strong>
            {device.current ? (
              <span className="rounded bg-ok-soft px-[7px] py-0.5 font-semibold text-[11px] text-ok uppercase tracking-[0.04em]">
                Este dispositivo
              </span>
            ) : null}
          </span>
          <span className="flex flex-wrap gap-x-[18px] gap-y-1 text-[13px] text-muted">
            <span>Inició sesión {signedInOn(device.created_at)}</span>
            <span>
              Último uso{" "}
              <strong className="font-semibold text-ink">
                {lastUse(device.last_seen_at, device.current)}
              </strong>
            </span>
            {device.last_ip ? (
              <span>
                IP <span className="font-mono">{device.last_ip}</span>
              </span>
            ) : null}
          </span>
        </div>
        {device.current ? null : (
          <button
            type="button"
            onClick={() => setAsking(true)}
            className="h-10 cursor-pointer rounded-md border border-line bg-white px-3.5 font-semibold text-[14px] text-bad"
          >
            Cerrar sesión
          </button>
        )}
      </div>
      {asking ? (
        <div
          role="alertdialog"
          aria-label="Confirmar cierre de sesión"
          className="mx-5 mb-4 flex flex-wrap items-center gap-x-4 gap-y-2.5 rounded-md border border-bad-line bg-bad-soft px-3.5 py-3 text-[14px] text-bad-ink-2 sm:ml-20"
        >
          <span className="min-w-[240px] flex-1">
            ¿Cerrar la sesión en <strong>{device.device_name}</strong>? Para volver a usarlo, vas a tener que
            ingresar de nuevo.
          </span>
          <button
            type="button"
            onClick={() => setAsking(false)}
            className="h-[38px] cursor-pointer rounded-md border border-line bg-white px-3 text-[14px]"
          >
            No, dejarla
          </button>
          <button
            type="button"
            disabled={close.isPending}
            onClick={() => close.mutate(device.id, { onSuccess: () => onClosed(device.device_name) })}
            className="h-[38px] cursor-pointer rounded-md border-0 bg-bad px-3 font-semibold text-[14px] text-white"
          >
            Sí, cerrar sesión
          </button>
        </div>
      ) : null}
    </li>
  );
}

function Skeleton() {
  return (
    <section aria-busy="true" className="overflow-hidden rounded-lg border border-line bg-white">
      {[60, 50].map((width, index) => (
        <div
          key={width}
          className={`grid grid-cols-[40px_minmax(0,1fr)] items-center gap-3 px-4 py-3.5 ${index ? "border-line-soft border-t" : ""}`}
        >
          <span className="block size-10 animate-shimmer rounded bg-line-soft" />
          <span className="flex flex-col gap-2">
            <span
              className="block h-3.5 animate-shimmer rounded bg-line-soft"
              style={{ width: `${width}%` }}
            />
            <span className="block h-3 w-4/5 animate-shimmer rounded bg-line-soft" />
          </span>
        </div>
      ))}
    </section>
  );
}

/** «Dispositivos conectados» (design board "Cuenta 8"). */
function Devices() {
  const devices = useDeviceSessions();
  const closeOthers = useCloseOtherSessions();
  const [flash, setFlash] = useState<string | null>(null);
  const list = devices.data ?? [];
  const others = list.filter((d) => !d.current);

  return (
    <main className="mx-auto flex max-w-[860px] flex-col gap-[18px] px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 font-bold text-[28px]">Dispositivos conectados</h1>
          <p className="m-0 text-[15px] text-ink-2">
            Dónde tienes la sesión abierta. Si no reconoces alguno, cierra su sesión.
          </p>
        </div>
        {others.length > 0 ? (
          <button
            type="button"
            disabled={closeOthers.isPending}
            onClick={() =>
              closeOthers.mutate(undefined, {
                onSuccess: () => setFlash("Cerramos la sesión en los demás dispositivos."),
              })
            }
            className="h-11 cursor-pointer rounded-md border border-bad bg-white px-4 font-semibold text-[14px] text-bad"
          >
            Cerrar sesión en los demás dispositivos
          </button>
        ) : null}
      </div>
      {flash ? (
        <div
          role="status"
          className="flex items-center gap-2.5 rounded-md border border-ok-line bg-ok-soft px-3.5 py-2.5 text-[14px] text-ok-ink"
        >
          <span aria-hidden>✓</span>
          {flash}
        </div>
      ) : null}
      {devices.isPending ? <Skeleton /> : null}
      {devices.isError ? (
        <section role="alert" className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4">
          <div className="rounded-md border border-bad-line bg-bad-soft px-3 py-2.5 text-[14px] text-bad-ink-2">
            <strong>No pudimos cargar tus dispositivos.</strong> Prueba de nuevo en un momento.
          </div>
          <button
            type="button"
            onClick={() => devices.refetch()}
            className="h-10 cursor-pointer self-start rounded-md border-0 bg-action px-3.5 font-semibold text-[14px] text-white"
          >
            Reintentar
          </button>
        </section>
      ) : null}
      {devices.data ? (
        <>
          <ul className="m-0 list-none overflow-hidden rounded-lg border border-line bg-white p-0">
            {list.map((device) => (
              <DeviceRow
                key={device.id}
                device={device}
                onClosed={(name) => setFlash(`Cerramos la sesión en ${name}.`)}
              />
            ))}
          </ul>
          {others.length === 0 ? (
            <p className="m-0 text-[13px] text-ink-2">Solo tienes la sesión abierta aquí.</p>
          ) : null}
          <p className="m-0 text-[13px] text-muted">
            Para cerrar la sesión en este dispositivo, usa «Cerrar sesión» del menú de tu cuenta.
          </p>
        </>
      ) : null}
    </main>
  );
}

export function DevicesPage() {
  return (
    <>
      <TopBar />
      <RequireSession>
        <Devices />
      </RequireSession>
    </>
  );
}
