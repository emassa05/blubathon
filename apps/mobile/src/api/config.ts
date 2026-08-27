/**
 * Configuración del acceso a la API. Todo entra por variables de entorno, así
 * que el mismo build sirve para desarrollo, demo y piloto.
 *
 * `VITE_BLUBATHON_API_URL` vacío es lo normal en desarrollo: las peticiones salen
 * como rutas relativas y el proxy de Vite (`vite.config.ts`) las lleva al
 * backend. Así el navegador ve un solo origen y CORS no entra en juego.
 */

/** Prefijo de la API. Vive en el registro de constantes (C02). */
export const PREFIJO_API = "/v1";

/** Origen del backend. Vacío = mismo origen (proxy de Vite o build servido junto a la API). */
export const ORIGEN_API = import.meta.env.VITE_BLUBATHON_API_URL ?? "";

export const BASE_API = `${ORIGEN_API}${PREFIJO_API}`;

/**
 * Niño que abre la pantalla. Sin valor, la app pregunta a `GET /v1/children` y
 * toma el primero: la demo no tiene selector y no queremos un UUID escrito a
 * mano en el código.
 *
 * `?child_id=` gana sobre la variable de entorno: la demo es mono-tenant y no
 * tiene selector, así que la URL es la forma de mirar a otro niño sin reiniciar
 * el servidor de desarrollo. Un id que no esté en la lista se ignora y se toma
 * el primero, igual que si no se hubiera pedido ninguno.
 */
export const ID_NINO =
  new URLSearchParams(window.location.search).get("child_id") ??
  import.meta.env.VITE_BLUBATHON_CHILD_ID ??
  "";

/** Corte de cada petición, en milisegundos. Sin esto una red caída cuelga la pantalla. */
export const TIMEOUT_MS = Number(import.meta.env.VITE_BLUBATHON_API_TIMEOUT_MS ?? 10_000);

/** Días de historial que pide la pantalla. El backend admite hasta 100. */
export const DIAS_HISTORIAL = 30;
