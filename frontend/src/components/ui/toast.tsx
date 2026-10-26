import { X } from "lucide-react";
import { create } from "zustand";

interface Toast {
  id: number;
  message: string;
  action?: { label: string; onClick: () => void };
}

interface ToastState {
  toasts: Toast[];
  show: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

// How long a notice stays on screen.
const TOAST_MS = 6000;

let nextId = 1;

export const useToasts = create<ToastState>()((set, get) => ({
  toasts: [],
  show: (toast) => {
    const id = nextId++;
    set({ toasts: [...get().toasts, { ...toast, id }] });
    window.setTimeout(() => get().dismiss(id), TOAST_MS);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

/** Short notices at the bottom, announced to screen readers. */
export function Toaster() {
  const { toasts, dismiss } = useToasts();
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-50 max-sm:bottom-24 flex flex-col items-center gap-2 px-4"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-md bg-ink px-4 py-3 text-white shadow-lg"
        >
          <span className="flex-1">{toast.message}</span>
          {toast.action && (
            <button
              type="button"
              className="font-semibold text-[#93B4FF] hover:underline"
              onClick={() => {
                toast.action?.onClick();
                dismiss(toast.id);
              }}
            >
              {toast.action.label}
            </button>
          )}
          <button type="button" aria-label="Cerrar aviso" onClick={() => dismiss(toast.id)}>
            <X size={16} aria-hidden />
          </button>
        </div>
      ))}
    </div>
  );
}
