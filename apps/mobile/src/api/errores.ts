import type { ErrorCode } from "@faro/contract/contract";
import { FARO_TEXTS_ES } from "@faro/contract/texts";

/**
 * Un fallo de la API, ya traducido.
 *
 * El backend responde los errores con un sobre estable
 * (`{ error: { code, message_es, request_id } }`, SPEC 11.7): código para el
 * código, mensaje en español para la persona y `request_id` para el soporte.
 * Esta clase es ese sobre más los dos casos que el sobre no cubre —la red y el
 * corte por tiempo—, para que la pantalla tenga siempre algo que mostrar.
 *
 * La abstención **no** llega por aquí: es HTTP 200 con estado explícito.
 */
export class ErrorFaro extends Error {
  /** Códigos del contrato más los dos locales. */
  readonly codigo: ErrorCode | "network_error" | "timeout";
  readonly mensajeEs: string;
  readonly estado: number | null;
  readonly requestId: string | null;

  constructor(opciones: {
    codigo: ErrorFaro["codigo"];
    mensajeEs: string;
    estado?: number | null;
    requestId?: string | null;
    causa?: unknown;
  }) {
    super(`${opciones.codigo}: ${opciones.mensajeEs}`, { cause: opciones.causa });
    this.name = "ErrorFaro";
    this.codigo = opciones.codigo;
    this.mensajeEs = opciones.mensajeEs;
    this.estado = opciones.estado ?? null;
    this.requestId = opciones.requestId ?? null;
  }

  /** El recurso no existe: la pantalla lo trata como vacío, no como fallo. */
  get esNoEncontrado(): boolean {
    return this.codigo === "not_found";
  }

  static red(causa: unknown): ErrorFaro {
    return new ErrorFaro({
      codigo: "network_error",
      mensajeEs: "No pudimos conectar con el servidor.",
      causa,
    });
  }

  static porTiempo(): ErrorFaro {
    return new ErrorFaro({
      codigo: "timeout",
      mensajeEs: "El servidor tardó demasiado en responder.",
    });
  }

  static inesperado(estado: number, requestId: string | null): ErrorFaro {
    return new ErrorFaro({
      codigo: "internal_error",
      mensajeEs: FARO_TEXTS_ES.genericErrorEs,
      estado,
      requestId,
    });
  }
}
