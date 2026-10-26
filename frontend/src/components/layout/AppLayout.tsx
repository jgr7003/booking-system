import { Outlet } from "@tanstack/react-router";
import { Toaster } from "@/components/ui/toast";

/** Shell of the app. Each screen renders its own top bar, as in the design. */
export function AppLayout() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Outlet />
      <Toaster />
    </div>
  );
}
