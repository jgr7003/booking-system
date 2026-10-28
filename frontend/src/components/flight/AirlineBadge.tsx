/** Code of the airline in a dark square (design). */
export function AirlineBadge({ code }: { code: string }) {
  return (
    <span className="data inline-flex h-[22px] w-[22px] items-center justify-center rounded bg-ink text-[10px] font-semibold text-white">
      {code}
    </span>
  );
}
