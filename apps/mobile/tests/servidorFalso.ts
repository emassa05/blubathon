import { vi } from "vitest";

/**
 * Un backend de mentira montado sobre `fetch`.
 *
 * Se intercepta `fetch` y no el módulo `@/api/blubathon` a propósito: así los tests
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

let rutasActuales: Rutas = {};
let rutasCambiadas: Rutas = {};

/**
 * Cambia lo que contesta **una** ruta, sin volver a instalar nada.
 *
 * Reinstalar el servidor cerraría el canal de eventos y con él el socket que la
 * pantalla ya tiene abierto, que es justo lo que se está probando cuando algo
 * cambia a mitad de un test: el RAG termina y la misma pantalla montada tiene
 * que enterarse.
 *
 * El cambio va en un mapa aparte y no encima del que se instaló, porque una
 * ruta puede estar declarada como getter —así es como varía su respuesta un test
 * que no necesita esto— y asignarle encima reventaría.
 */
export function declararRuta(ruta: string, respuesta: RespuestaFalsa | unknown): void {
  rutasCambiadas[ruta] = respuesta;
}

/**
 * Y el doble del canal de eventos (`GET /v1/ws`).
 *
 * Va junto al de `fetch` porque monta la misma pantalla: `useResumenSalud` abre
 * el socket al montarse, y en jsdom `WebSocket` existe pero no hay servidor al
 * otro lado, así que cada test dejaría una conexión fallando y reintentando
 * cada tres segundos. Con el doble no se conecta a ningún sitio y además los
 * tests pueden empujar un evento, que es la única forma de comprobar que la
 * pantalla reacciona sin recargarse.
 */
type Escucha = (evento: unknown) => void;

class SocketFalso {
  static abiertos: SocketFalso[] = [];

  private readonly escuchas = new Map<string, Set<Escucha>>();

  constructor(readonly url: string) {
    SocketFalso.abiertos.push(this);
  }

  addEventListener(tipo: string, escucha: Escucha): void {
    const registradas = this.escuchas.get(tipo) ?? new Set<Escucha>();
    registradas.add(escucha);
    this.escuchas.set(tipo, registradas);
  }

  close(): void {
    SocketFalso.abiertos = SocketFalso.abiertos.filter((socket) => socket !== this);
  }

  recibir(datos: string): void {
    for (const escucha of this.escuchas.get("message") ?? []) escucha({ data: datos });
  }
}

/** Empuja un evento por el canal, como haría el backend al terminar el RAG. */
export function emitirEvento(evento: unknown): void {
  const datos = JSON.stringify(evento);
  for (const socket of [...SocketFalso.abiertos]) socket.recibir(datos);
}

/**
 * Instala el doble. Las claves son la ruta sin query (`/v1/children`); lo que
 * no esté declarado responde 404 con el sobre de error del backend.
 */
export function instalarServidorFalso(rutas: Rutas): void {
  // Por referencia y sin copiar: hay rutas declaradas como getter, que varían su
  // respuesta entre un caso y otro, y una copia las congelaría en el valor que
  // tuvieran al instalar.
  rutasActuales = rutas;
  rutasCambiadas = {};
  SocketFalso.abiertos = [];
  vi.stubGlobal("WebSocket", SocketFalso);
  vi.stubGlobal(
    "fetch",
    vi.fn((entrada: string | URL | Request) => {
      const url = new URL(String(entrada), "http://localhost");
      const declarada =
        url.pathname in rutasCambiadas ? rutasCambiadas[url.pathname] : rutasActuales[url.pathname];
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

/** El episodio de una solicitud, para poder declarar su ruta de reporte. */
export function idEpisodioFalso(sufijo = "a"): string {
  return `2222222${sufijo}-2222-4222-8222-222222222222`;
}

/**
 * Una solicitud de resultado abierta: la pregunta de cierre que deja cada día
 * registrado. Los dos plazos se dan en horas desde ahora, porque lo que decide
 * si se puede contestar no es la fecha sino dónde cae el reloj: negativo es
 * "ya pasó".
 *
 * `sufijo` distingue una solicitud de otra cuando hay dos abiertas a la vez
 * —la del envío de ayer y la del de hoy—, que es el caso normal desde que la
 * pantalla las ofrece todas.
 */
export function solicitudFalsa(opciones: {
  finVentanaEnHoras: number;
  vencimientoEnHoras: number;
  ninoId?: string;
  sufijo?: string;
}): unknown {
  const enHoras = (horas: number) => new Date(Date.now() + horas * 3_600_000).toISOString();
  const sufijo = opciones.sufijo ?? "a";
  return {
    outcome_request_id: `4444444${sufijo}-4444-4444-8444-444444444444`,
    prediction_episode_id: idEpisodioFalso(sufijo),
    subject_id: opciones.ninoId ?? ID_NINO_FALSO,
    target_definition_version: "1.0.0",
    question_es: "¿Hubo un evento de desregulación en las últimas 24 horas?",
    severity_anchors_es: ["Necesitó apoyo de una persona para volver a la calma."],
    target_start_at: enHoras(opciones.finVentanaEnHoras - 24),
    target_end_at: enHoras(opciones.finVentanaEnHoras),
    capture_deadline_at: enHoras(opciones.vencimientoEnHoras),
    state: "open",
    resolution_status: "unresolved",
  };
}
