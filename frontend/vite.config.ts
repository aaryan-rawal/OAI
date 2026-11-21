/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Read the root project .env so VITE_GOOGLE_MAPS_EMBED_KEY works without duplicating secrets.
  // Only VITE_-prefixed variables are exposed to browser code.
  envDir: "..",
  plugins: [react()],
  server: {
    port: 5173,
    // Backend API proxy for the integrated application
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
