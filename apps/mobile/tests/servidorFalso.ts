import { vi } from "vitest";

/**
 * Un backend de mentira montado sobre `fetch`.
 *
 * Se intercepta `fetch` y no el módulo `@/api/faro` a propósito: así los tests
 * de la pantalla recorren el mismo camino que el navegador —transporte, sobre
 * de error, adaptador— y no solo el último tramo. Cambiar la forma de una
 * respuesta rompe aquí, que es donde tiene que romper.
 */

export const ID_NINO_FALSO = "00000000-0000-4000-8000-000000000101";

export interface RespuestaFalsa {
  readonly estado?: number;
  readonly cuerpo: unknown;
}

export type Rutas = Record<string, RespuestaFalsa | unknown>;

function resolver(entrada: RespuestaFalsa | unknown): RespuestaFalsa {
  return typeof entrada === "object" && entrada !== null && "cuerpo" in entrada
    ? (entrada as RespuestaFalsa)
    : { cuerpo: entrada };
}

function sobreDeError(codigo: string): unknown {
  return {
    error: {
      code: codigo,
      message_es: "No encontramos el recurso solicitado.",
      request_id: "test",
    },
  };
}

/**
 * Instala el doble. Las claves son la ruta sin query (`/v1/children`); lo que
 * no esté declarado responde 404 con el sobre de error del backend.
 */
export function instalarServidorFalso(rutas: Rutas): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((entrada: string | URL | Request) => {
      const url = new URL(String(entrada), "http://localhost");
      const declarada = rutas[url.pathname];
      const { estado = 200, cuerpo } =
        declarada === undefined
          ? { estado: 404, cuerpo: sobreDeError("not_found") }
          : resolver(declarada);

      return Promise.resolve(
        new Response(JSON.stringify(cuerpo), {
          status: estado,
          headers: { "Content-Type": "application/json", "X-Request-Id": "test" },
        }),
      );
    }),
  );
}

/* Respuestas de referencia, con la forma exacta que devuelve `apps/api`. */

export function historialFalso(dias: unknown[]): unknown {
  return { child_id: ID_NINO_FALSO, days: dias };
}

export function diaFalso(opciones: {
  fecha: string;
  probabilidad?: number | null;
  intervalo?: readonly [number, number] | null;
  conRecomendacion?: boolean;
}): unknown {
  const estimado = typeof opciones.probabilidad === "number";
  return {
    local_date: opciones.fecha,
    submission_id: "11111111-1111-4111-8111-111111111111",
    prediction_episode_id: "22222222-2222-4222-8222-222222222222",
    prediction: {
      status: estimado ? "ok" : "abstained",
      probability: opciones.probabilidad ?? null,
      interval: opciones.intervalo ?? null,
    },
    recommendation: opciones.conRecomendacion
      ? {
          recommendation_instance_id: "33333333-3333-4333-8333-333333333333",
          status: "matched",
          rating: null,
        }
      : null,
    outcome: { status: "pending", reported_at: null },
  };
}

export function planFalso(destacados: readonly string[]): unknown {
  return {
    questions: destacados.map((codigo) => ({
      field_code: codigo,
      highlighted: true,
      reason: "staleness",
      voi_nats: null,
    })),
    defaults: [],
    coverage: 0.4,
  };
}
