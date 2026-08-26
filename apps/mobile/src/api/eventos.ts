/**
 * El canal de eventos del backend (`GET /v1/ws`).
 *
 * El RAG corre **después** de guardar el formulario, así que la recomendación
 * no viaja en la respuesta del `POST`: llega por aquí cuando está lista. Lo
 * mismo con la redacción que dispara una valoración negativa.
 *
 * La pantalla Salud todavía no reacciona a estos eventos —hoy solo lee un día—
 * pero el canal queda montado y tipado para cuando el formulario entre.
 */

import { BASE_API, ORIGEN_API } from "@/api/config";

export type EventoFaro =
  | {
      type: "recommendation.ready";
      child_id: string;
      prediction_episode_id: string;
      recommendation_instance_id: string;
      status: "pending" | "matched" | "abstained";
      abstention_reason: string | null;
      at: string;
    }
  | {
      type: "recommendation.redrafted";
      recommendation_instance_id: string;
      attempt: number;
      status: "pending" | "matched" | "abstained";
      at: string;
    }
  | {
      type: "feedback.recorded";
      recommendation_instance_id: string;
      rating: "good" | "bad";
      at: string;
    };

const RECONEXION_MS = 3_000;

function urlDelCanal(): string {
  const base = ORIGEN_API || window.location.origin;
  return `${new URL(BASE_API, base).toString().replace(/^http/, "ws")}/ws`;
}

/**
 * Se suscribe a los eventos y devuelve la función que corta la suscripción.
 *
 * Reconecta sola: el backend cierra el socket al recargarse y sin esto la
 * pantalla se queda muda hasta que alguien recargue la página. Cerrar desde
 * aquí no reconecta.
 */
export function conectarEventos(alRecibir: (evento: EventoFaro) => void): () => void {
  let socket: WebSocket | null = null;
  let temporizador: ReturnType<typeof setTimeout> | null = null;
  let cerrado = false;

  function abrir(): void {
    socket = new WebSocket(urlDelCanal());

    socket.addEventListener("message", (mensaje) => {
      // Un mensaje ilegible no puede tumbar el canal.
      try {
        alRecibir(JSON.parse(mensaje.data as string) as EventoFaro);
      } catch {
        return;
      }
    });

    socket.addEventListener("close", () => {
      if (cerrado) return;
      temporizador = setTimeout(abrir, RECONEXION_MS);
    });
  }

  abrir();

  return () => {
    cerrado = true;
    if (temporizador !== null) clearTimeout(temporizador);
    socket?.close();
  };
}
