import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { LogoIcon } from "@/components/icons";
import { cn } from "@/lib/cn";

/**
 * Dark bar at the top of every screen (design: #111827). Each screen fills it with its own
 * content: search summary, steps, expiry...
 */
export function TopBar({ children, className }: { children?: ReactNode; className?: string }) {
  return (
    <header className="bg-ink text-white">
      <div
        className={cn(
          "mx-auto flex min-h-[60px] max-w-[1240px] flex-wrap items-center gap-x-5 gap-y-2.5 px-4 py-2 sm:px-5",
          className,
        )}
      >
        <Link to="/" className="flex items-center gap-2.5 text-[18px] font-bold text-white hover:text-white">
          <LogoIcon />
          Vuelos
        </Link>
        {children}
      </div>
    </header>
  );
}

/** Vertical divider between items of the dark bar. */
export function BarDivider() {
  return <span aria-hidden className="h-5 w-px bg-header-line" />;
}

/** Thin progress bar under the top bar while searching. */
export function ProgressBar({ label }: { label: string }) {
  return (
    <div role="progressbar" aria-label={label} className="h-[3px] overflow-hidden bg-action-line">
      <div className="h-[3px] w-2/5 animate-progress bg-action" />
    </div>
  );
}
