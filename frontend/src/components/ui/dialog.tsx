import { Dialog as RadixDialog } from "radix-ui";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface DialogProps {
  open: boolean;
  title: ReactNode;
  children: ReactNode;
  /** Called on Escape, outside click or the close button; omit for a dialog that needs an explicit choice. */
  onClose?: () => void;
  /** Width and layout overrides, e.g. a wide dialog for the fare matrix. */
  className?: string;
  /** No padding: the title gets its own bordered bar and the content manages its spacing. */
  flush?: boolean;
}

/** Modal dialog of the design (white card, 8 px radius, large soft shadow). */
export function Dialog({ open, title, children, onClose, className, flush = false }: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={(next) => !next && onClose?.()}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/40" />
        <RadixDialog.Content
          aria-describedby={undefined}
          onEscapeKeyDown={(e) => !onClose && e.preventDefault()}
          onInteractOutside={(e) => !onClose && e.preventDefault()}
          className={cn(
            "fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100vh-32px)] w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 flex-col gap-2.5 overflow-y-auto rounded-lg border border-line bg-white shadow-dialog",
            flush ? "p-0" : "p-[18px]",
            className,
          )}
        >
          <div
            className={cn(
              "flex items-start justify-between gap-3",
              flush && "sticky top-0 z-10 border-b border-line-soft bg-white px-5 py-3",
            )}
          >
            <RadixDialog.Title className="text-[16px] font-semibold">{title}</RadixDialog.Title>
            {onClose && (
              <RadixDialog.Close
                aria-label="Cerrar"
                className="h-9 w-9 shrink-0 rounded-md border border-line bg-white text-[18px] leading-none"
              >
                ×
              </RadixDialog.Close>
            )}
          </div>
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
