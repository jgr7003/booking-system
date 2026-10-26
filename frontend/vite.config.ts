/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Where the dev server forwards /api: the backend service inside docker compose.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    // The compose service name, so other containers (e.g. browser tests) can reach the dev server.
    allowedHosts: ["frontend"],
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
    // Bind mounts from Windows/macOS don't propagate file events into the container.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true", interval: 300 },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
