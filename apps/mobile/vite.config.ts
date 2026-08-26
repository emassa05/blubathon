import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // El contrato ejecutable de `packages/shared/generated`: tipos, catálogo
      // de campos, textos y constantes. Se importa por alias en vez de
      // copiarse, porque nada del contrato se declara dos veces.
      "@contrato": fileURLToPath(new URL("../../packages/shared/generated", import.meta.url)),
    },
  },
  server: {
    /*
     * La API acepta CORS solo desde una allowlist explícita y su valor por
     * defecto es el puerto 3000 (`apps/api/settings.py: DEFAULT_CORS_ORIGINS`).
     * Servir aquí en 3000 evita tocar el backend; la alternativa es arrancar la
     * API con `FARO_CORS_ORIGINS=http://localhost:5173`.
     */
    port: 3000,
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"],
  },
});
