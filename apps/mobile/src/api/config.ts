/**
 * Configuración del acceso a la API. Todo entra por variables de entorno, así
 * que el mismo build sirve para desarrollo, demo y piloto.
 *
 * `VITE_FARO_API_URL` vacío es lo normal en desarrollo: las peticiones salen
 * como rutas relativas y el proxy de Vite (`vite.config.ts`) las lleva al
 * backend. Así el navegador ve un solo origen y CORS no entra en juego.
 */

/** Prefijo de la API. Vive en el registro de constantes (SPEC 11 / C02). */
export const PREFIJO_API = "/v1";

/** Origen del backend. Vacío = mismo origen (proxy de Vite o build servido junto a la API). */
export const ORIGEN_API = import.meta.env.VITE_FARO_API_URL ?? "";

export const BASE_API = `${ORIGEN_API}${PREFIJO_API}`;

/**
 * Niño que abre la pantalla. Sin valor, la app pregunta a `GET /v1/children` y
 * toma el primero: la demo no tiene selector y no queremos un UUID escrito a
 * mano en el código.
 */
export const ID_NINO = import.meta.env.VITE_FARO_CHILD_ID ?? "";

/** Corte de cada petición, en milisegundos. Sin esto una red caída cuelga la pantalla. */
export const TIMEOUT_MS = Number(import.meta.env.VITE_FARO_API_TIMEOUT_MS ?? 10_000);

/** Días de historial que pide la pantalla. El backend admite hasta 100. */
export const DIAS_HISTORIAL = 30;
