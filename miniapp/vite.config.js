import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The app is served by FastAPI under /app/, so every asset URL must be
// relative to that prefix rather than to the domain root.
export default defineConfig({
  plugins: [react()],
  base: "/app/",
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    // `npm run dev` talks to a locally running API. Only the paths the app
    // actually calls are proxied, so a typo in a fetch URL fails loudly here
    // instead of being silently swallowed by a catch-all.
    proxy: Object.fromEntries(
      [
        "/auth",
        "/users",
        "/avatar",
        "/clothing",
        "/wardrobe",
        "/competitions",
        "/competition-requests",
        "/leaderboard",
        "/notifications",
        "/qr",
        "/media",
        "/config",
      ].map((path) => [path, { target: "http://127.0.0.1:8000", changeOrigin: true }])
    ),
  },
});
