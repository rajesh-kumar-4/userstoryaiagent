/// <reference types="vitest/config" />
import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";

const here = path.dirname(fileURLToPath(import.meta.url));

// The UI calls the backend through the "/api" prefix. In development the Vite
// proxy strips that prefix and forwards to the FastAPI service. In production
// the nginx config in this folder does the same job.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, here, "");
  const backendTarget = env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(here, "src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
      },
    },
    build: {
      target: "es2022",
      sourcemap: false,
      chunkSizeWarningLimit: 1200,
    },
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
      globals: false,
    },
  };
});
