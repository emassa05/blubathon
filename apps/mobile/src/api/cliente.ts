/**
 * Cliente HTTP de la API de Blubathon (v0.4).
 *
 * La aplicación solo consume el contrato publicado por la API: nunca abre la
 * base ni carga artefactos. Este módulo es la única frontera de red del
 * frontend, y no inventa ni un endpoint más de los que expone
 * `apps/api/routes/v1.py`.
 *
 * Dos detalles del servidor que este cliente respeta al pie de la letra:
 *
 * - La API no pide autenticación en v0.4 (tenant fijo), así que no se manda
 *   ninguna cabecera de sesión.
 * - CORS solo permite `Content-Type` (`apps/api/main.py`), así que ninguna
 *   petición añade cabeceras propias: una sola cabecera extra convertiría el
 *   preflight en un fallo.
 */

import { BASE_API } from "@/api/config";
import { BLUBATHON_TEXTS_ES, type ErrorResponse } from "@/api/contrato";

/** Base de la API, con el prefijo `/v1` que declara la constante C02. */
export const API_BASE = BASE_API;

/** Milisegundos antes de dar la petición por perdida. */
const TIEMPO_LIMITE = 10_000;

/**
 * Un fallo de la API con su código del contrato.
 *
 * `codigo` es `network_error` cuando la petición ni siquiera llegó: es la única
 * forma de distinguir "la API dijo que no" de "la API no está".
 */
export class ErrorApi extends Error {
  readonly codigo: string;
  readonly estado: number;
  readonly requestId: string;

  constructor(estado: number, cuerpo: ErrorResponse | null) {
    super(cuerpo?.error.message_es ?? BLUBATHON_TEXTS_ES.genericErrorEs);
    this.name = "ErrorApi";
    this.estado = estado;
    this.codigo = cuerpo?.error.code ?? "network_error";
    this.requestId = cuerpo?.error.request_id ?? "";
  }

  /** No hubo respuesta: la API está apagada, en otro puerto o bloqueada por CORS. */
  get sinConexion(): boolean {
    return this.estado === 0;
  }
}

interface Opciones {
  metodo?: "GET" | "POST";
  cuerpo?: unknown;
  signal?: AbortSignal;
}

export async function peticion<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const metodo = opciones.metodo ?? "GET";
  const abortador = new AbortController();
  const temporizador = setTimeout(() => abortador.abort(), TIEMPO_LIMITE);
  opciones.signal?.addEventListener("abort", () => abortador.abort());

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE}${ruta}`, {
      method: metodo,
      headers: metodo === "POST" ? { "Content-Type": "application/json" } : undefined,
      body: metodo === "POST" ? JSON.stringify(opciones.cuerpo ?? {}) : undefined,
      signal: abortador.signal,
    });
  } catch {
    throw new ErrorApi(0, null);
  } finally {
    clearTimeout(temporizador);
  }

  if (!respuesta.ok) {
    // El sobre de error del contrato: `{ error: { code, message_es, request_id } }`.
    let cuerpo: ErrorResponse | null = null;
    try {
      cuerpo = (await respuesta.json()) as ErrorResponse;
    } catch {
      cuerpo = null;
    }
    throw new ErrorApi(respuesta.status, cuerpo);
  }

  return (await respuesta.json()) as T;
}

/** El mensaje que se le enseña a una persona cuando algo falla. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) {
    return error.sinConexion
      ? "No hay conexión con la API de Blubathon. Los datos que ves son los guardados en este dispositivo."
      : error.message;
  }
  return BLUBATHON_TEXTS_ES.genericErrorEs;
}
