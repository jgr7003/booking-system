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
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        // The API picks the installation (platform or organization) from the host the browser
        // used, e.g. acme.localhost; changeOrigin rewrites Host, so pass the original along,
        // with the address of the browser.
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq, req) => {
            if (req.headers.host) proxyReq.setHeader("x-forwarded-host", req.headers.host);
            // The real client, so the API can block abusive addresses instead of the proxy's.
            if (req.socket.remoteAddress) proxyReq.setHeader("x-forwarded-for", req.socket.remoteAddress);
          });
        },
      },
    },
    // Bind mounts from Windows/macOS don't propagate file events into the container.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true", interval: 300 },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
