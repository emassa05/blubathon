/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origen del backend. Vacío en desarrollo: manda el proxy de Vite. */
  readonly VITE_BLUBATHON_API_URL?: string;
  /** Niño que abre la pantalla. Sin valor, se toma el primero de `GET /v1/children`. */
  readonly VITE_BLUBATHON_CHILD_ID?: string;
  /** Corte de cada petición, en milisegundos. */
  readonly VITE_BLUBATHON_API_TIMEOUT_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
