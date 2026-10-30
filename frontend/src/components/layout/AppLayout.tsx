import { Outlet } from "@tanstack/react-router";
import { useEffect } from "react";
import { bootstrapSession } from "@/api/auth";
import { InstallationGate } from "@/components/layout/RequireSession";
import { Toaster } from "@/components/ui/toast";

/** Shell of the app. Each screen renders its own top bar, as in the design. */
export function AppLayout() {
  // Restores the session of this device, if it has one (refresh token in IndexedDB).
  useEffect(() => {
    void bootstrapSession();
  }, []);
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <InstallationGate>
        <Outlet />
      </InstallationGate>
      <Toaster />
    </div>
  );
}
