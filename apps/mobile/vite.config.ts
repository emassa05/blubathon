import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

/**
 * En desarrollo el navegador ve un solo origen: `/v1` y `/health` salen del
 * mismo `localhost:5173` y el proxy los lleva al backend. Así no hay preflight
 * ni allowlist de CORS que mantener en dos sitios (`apps/api/settings.py`).
 *
 * `VITE_FARO_API_URL` apunta al backend directamente y desactiva el proxy: es
 * el camino del build, donde ya no hay servidor de desarrollo.
 */
const BACKEND_POR_DEFECTO = "http://127.0.0.1:8000";

export default defineConfig(({ mode }) => {
  // Sin prefijo `VITE_`: esto lo usa el servidor de desarrollo, no el cliente,
  // y no tiene por qué acabar en el bundle.
  const env = loadEnv(mode, process.cwd(), "FARO_");
  const backend = env.FARO_BACKEND_URL || BACKEND_POR_DEFECTO;

  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      proxy: {
        "/v1": { target: backend, changeOrigin: true, ws: true },
        "/health": { target: backend, changeOrigin: true },
      },
    },
    test: {
      environment: "jsdom",
      include: ["tests/**/*.test.ts"],
    },
  };
});
