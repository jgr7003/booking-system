import { manageRows, type Order } from "./logic";
import { CARD, KICKER } from "./styles";

/** "Gestionar reserva": what the airline allows, explained. Not actions yet: no focus, no disabled buttons. */
export function Manage({ order, reference }: { order: Order; reference: string }) {
  const rows = manageRows(order);
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby="manage" className={`${CARD} flex flex-col gap-2.5 px-[18px] py-4 max-sm:p-3.5`}>
      <div className="flex items-center justify-between gap-2">
        <h2 id="manage" className={KICKER}>
          Gestionar reserva
        </h2>
        <span className="rounded bg-action-soft px-[7px] py-[3px] text-[11px] font-semibold tracking-[0.04em] text-action-hover uppercase">
          Próximamente
        </span>
      </div>
      <p className="text-[13px] leading-[1.45] text-ink-2">
        Pronto vas a poder hacer esto desde acá. Mientras tanto, consultá a {order.owner.name} con tu código{" "}
        {reference}.
      </p>
      <ul className="flex flex-col gap-1.5">
        {rows.map((row) => (
          <li
            key={row.key}
            className="flex items-start gap-2.5 rounded-md border border-dashed border-line-dash px-3 py-2.5"
          >
            <span aria-hidden className="mt-px flex-none text-muted">
              {row.icon}
            </span>
            <span className="flex flex-col gap-0.5 text-[14px]">
              <strong className="font-semibold">{row.title}</strong>
              <span className="text-[12px] text-muted">{row.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
