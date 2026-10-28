import { CARD } from "./styles";

export function BeforeFlying({
  passenger,
  airline,
  reference,
}: {
  passenger: string;
  airline: string;
  reference: string;
}) {
  const steps: [string, string][] = [
    ["Llevá tu documento.", ` El nombre tiene que coincidir con el del ticket: ${passenger}.`],
    [`Hacé el check-in con ${airline}`, `, que es quien opera los vuelos, usando el código ${reference}.`],
    ["Llegá con tiempo al aeropuerto.", " Revisá con la aerolínea cuánto antes conviene presentarse."],
  ];
  return (
    <section aria-labelledby="before" className={`${CARD} flex flex-col gap-3 px-5 py-[18px] max-sm:p-3.5`}>
      <h2 id="before" className="text-[16px] font-bold sm:text-[18px]">
        Antes de volar
      </h2>
      <ol className="grid grid-cols-3 gap-3 max-sm:grid-cols-1 max-sm:gap-2.5">
        {steps.map(([strong, rest], i) => (
          <li key={strong} className="flex items-start gap-2.5">
            <span className="inline-flex h-[26px] w-[26px] flex-none items-center justify-center rounded-full bg-action-soft font-mono text-[13px] font-semibold text-action">
              {i + 1}
            </span>
            <span className="text-[14px] leading-[1.45]">
              <strong>{strong}</strong>
              {rest}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
