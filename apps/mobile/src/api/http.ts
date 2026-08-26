import type { ErrorResponse } from "@faro/contract/contract";

import { BASE_API, TIMEOUT_MS } from "@/api/config";
import { ErrorFaro } from "@/api/errores";

type Metodo = "GET" | "POST";

interface Opciones {
  readonly metodo?: Metodo;
  readonly cuerpo?: unknown;
  readonly consulta?: Record<string, string | number | undefined>;
  /** Cancelación del llamador. Se combina con el corte por tiempo. */
  readonly signal?: AbortSignal;
}

function ruta(camino: string, consulta: Opciones["consulta"]): string {
  const url = `${BASE_API}${camino}`;
  if (!consulta) return url;

  const parametros = new URLSearchParams();
  for (const [clave, valor] of Object.entries(consulta)) {
    if (valor !== undefined) parametros.set(clave, String(valor));
  }
  const cadena = parametros.toString();
  return cadena ? `${url}?${cadena}` : url;
}

function esSobreDeError(cuerpo: unknown): cuerpo is ErrorResponse {
  return (
    typeof cuerpo === "object" &&
    cuerpo !== null &&
    "error" in cuerpo &&
    typeof (cuerpo as ErrorResponse).error?.code === "string"
  );
}

async function traducirFallo(respuesta: Response): Promise<ErrorFaro> {
  const requestId = respuesta.headers.get("X-Request-Id");
  // El cuerpo puede no ser JSON: un proxy o un 502 responden HTML.
  const cuerpo = await respuesta.json().catch(() => null);
  if (!esSobreDeError(cuerpo)) return ErrorFaro.inesperado(respuesta.status, requestId);

  return new ErrorFaro({
    codigo: cuerpo.error.code,
    mensajeEs: cuerpo.error.message_es,
    estado: respuesta.status,
    requestId: cuerpo.error.request_id || requestId,
  });
}

/**
 * Una petición a la API, ya tipada y con los fallos traducidos.
 *
 * Es el único sitio del frontend que conoce `fetch`, cabeceras y códigos HTTP.
 * Todo lo que sale de aquí es o el cuerpo tipado o un `ErrorFaro`.
 *
 * El tipo de respuesta se toma del contrato generado (`@faro/contract`), que
 * sale del mismo esquema que valida el backend: si el contrato cambia, el
 * frontend deja de compilar. No hay validación en tiempo de ejecución a
 * propósito —el contrato es la puerta— y `T` es por tanto una afirmación, no
 * una comprobación.
 */
export async function pedir<T>(camino: string, opciones: Opciones = {}): Promise<T> {
  const porTiempo = AbortSignal.timeout(TIMEOUT_MS);
  const signal = opciones.signal ? AbortSignal.any([opciones.signal, porTiempo]) : porTiempo;

  let respuesta: Response;
  try {
    respuesta = await fetch(ruta(camino, opciones.consulta), {
      method: opciones.metodo ?? "GET",
      signal,
      headers: opciones.cuerpo === undefined ? undefined : { "Content-Type": "application/json" },
      body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
    });
  } catch (causa) {
    // Cancelar es una decisión del llamador, no un fallo: se propaga tal cual
    // para que el composable pueda distinguirla y no pintar un error.
    if (opciones.signal?.aborted) throw causa;
    if (porTiempo.aborted) throw ErrorFaro.porTiempo();
    throw ErrorFaro.red(causa);
  }

  if (!respuesta.ok) throw await traducirFallo(respuesta);
  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}
