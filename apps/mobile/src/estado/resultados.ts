/**
 * Los resultados que quedan por reportar.
 *
 * Es la mitad del ciclo que faltaba. Un cuestionario abre un **episodio**, que
 * es la pregunta: "¿habrá una desregulación en las próximas 24 horas?". El
 * resultado es la respuesta, y llega por otra vía. Sin ella el baseline
 * personal se queda en cero resultados verificados para siempre y nunca da
 * cifra (SPEC 8.5 / C19, cinco).
 *
 * Dos reglas de SPEC 4.4 deciden qué se puede ofrecer y cuándo, y no son un
 * detalle de presentación: un reporte fuera de plazo se guarda pero **no
 * resuelve**, así que un botón que se pueda pulsar antes de tiempo produce un
 * envío que parece funcionar y no cuenta para nada.
 *
 * - Un `no` solo cuenta reportado `on_time`: a partir de que cierra la ventana
 *   del objetivo y hasta el vencimiento de captura.
 * - Un `yes` cuenta también antes, pero su `occurred_at` tiene que caer dentro
 *   de `(inicio, fin]`.
 */

import { computed, ref } from "vue";

import type { OutcomeReportValue, OutcomeRequestView } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { listarSolicitudesDeResultado, reportarResultado } from "@/api/faro";

const solicitudes = ref<readonly OutcomeRequestView[]>([]);
const cargado = ref(false);
const enviando = ref<string | null>(null);
const error = ref<string | null>(null);

async function pedir(): Promise<void> {
  error.value = null;
  try {
    const respuesta = await listarSolicitudesDeResultado();
    solicitudes.value = respuesta.items ?? [];
    cargado.value = true;
  } catch (fallo) {
    error.value = mensajeDeError(fallo);
  }
}

/** ¿Ya cerró la ventana de 24 h del objetivo? Solo entonces un `no` resuelve. */
export function ventanaCerrada(solicitud: OutcomeRequestView, ahora = new Date()): boolean {
  return ahora.getTime() >= Date.parse(solicitud.target_end_at);
}

/**
 * El instante que se declara como momento del episodio.
 *
 * Tiene que caer dentro de `(inicio, fin]`. Si la ventana ya cerró, el último
 * instante válido es su propio fin; si sigue abierta, ahora mismo lo está.
 */
export function momentoDelEpisodio(solicitud: OutcomeRequestView, ahora = new Date()): string {
  const fin = Date.parse(solicitud.target_end_at);
  return new Date(Math.min(ahora.getTime(), fin)).toISOString();
}

/** Vacía lo pedido. Solo lo usan las pruebas: el estado es de módulo. */
export function olvidarResultados(): void {
  solicitudes.value = [];
  cargado.value = false;
  enviando.value = null;
  error.value = null;
}

export function useResultados() {
  /** La solicitud abierta de esa persona, si la hay. */
  function pendienteDe(ninoId: string | null): OutcomeRequestView | null {
    if (ninoId === null) return null;
    return (
      solicitudes.value.find((item) => item.subject_id === ninoId && item.state === "open") ?? null
    );
  }

  async function reportar(
    solicitud: OutcomeRequestView,
    valor: OutcomeReportValue,
  ): Promise<boolean> {
    enviando.value = solicitud.outcome_request_id;
    error.value = null;
    try {
      await reportarResultado(solicitud.prediction_episode_id, {
        value: valor,
        // `occurred_at` solo se manda con `yes`: con `no` el backend lo
        // rechaza explícito (`outcome_occurred_at_forbidden`).
        occurred_at: valor === "yes" ? momentoDelEpisodio(solicitud) : null,
      });
      await pedir();
      return true;
    } catch (fallo) {
      error.value = mensajeDeError(fallo);
      return false;
    } finally {
      enviando.value = null;
    }
  }

  function cargar(forzar = false): Promise<void> {
    if (!forzar && cargado.value) return Promise.resolve();
    return pedir();
  }

  return {
    solicitudes,
    cargado,
    error,
    enviando: computed(() => enviando.value),
    pendienteDe,
    reportar,
    cargar,
  };
}
