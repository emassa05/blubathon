/**
 * Los resultados que quedan por reportar.
 *
 * Es la mitad del ciclo que faltaba. Un cuestionario abre un **episodio**, que
 * es la pregunta: "¿habrá una desregulación en las próximas 24 horas?". El
 * resultado es la respuesta, y llega por otra vía. Sin ella el baseline
 * personal se queda en cero resultados verificados para siempre y nunca da
 * cifra (C19, cinco).
 *
 * Lo que decide si un reporte cuenta —y no es un detalle de presentación, que
 * un reporte que no resuelve se guarda igual y parece haber funcionado:
 *
 * - Un `no` resuelve en cuanto se da, con la ventana abierta o cerrada. El
 *   `timing_status` guarda que llegó `early`, pero la resolución sale (ver
 *   `compute_resolution` en el backend).
 * - Un `yes` resuelve también, con su `occurred_at` dentro de `(inicio, fin]`.
 * - Lo único que no resuelve es lo que llega después del vencimiento de
 *   captura, a las 48 h. Ahí la API ya ni lo devuelve en la lista.
 */

import { computed, ref } from "vue";

import type { OutcomeReportValue, OutcomeRequestView } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { listarSolicitudesDeResultado, reportarResultado } from "@/api/blubathon";

const solicitudes = ref<readonly OutcomeRequestView[]>([]);
const cargado = ref(false);
const enviando = ref<string | null>(null);
const error = ref<string | null>(null);
/**
 * De qué solicitud habla el `error`, cuando habla de una.
 *
 * Con varias preguntas en pantalla, un único mensaje suelto no dice cuál de
 * ellas falló y lo pintarían todas. `null` es el fallo al pedir la lista, que
 * no es de ninguna en particular.
 */
const solicitudDelError = ref<string | null>(null);

async function pedir(): Promise<void> {
  error.value = null;
  solicitudDelError.value = null;
  try {
    const respuesta = await listarSolicitudesDeResultado();
    solicitudes.value = respuesta.items ?? [];
    cargado.value = true;
  } catch (fallo) {
    error.value = mensajeDeError(fallo);
  }
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
  solicitudDelError.value = null;
}

export function useResultados() {
  /**
   * Todas las preguntas abiertas de esa persona, en el orden en que la API las
   * da: por vencimiento, primero la que menos plazo le queda.
   *
   * Son todas y no la primera porque puede haber dos a la vez —la del envío de
   * ayer, que sigue sin contestar, y la que abrió el de hoy— y quedarse con una
   * dejaba la otra sin manera de contestarse hasta que la primera venciera.
   */
  function pendientesDe(ninoId: string | null): readonly OutcomeRequestView[] {
    if (ninoId === null) return [];
    return solicitudes.value.filter((item) => item.subject_id === ninoId && item.state === "open");
  }

  async function reportar(
    solicitud: OutcomeRequestView,
    valor: OutcomeReportValue,
  ): Promise<boolean> {
    enviando.value = solicitud.outcome_request_id;
    error.value = null;
    solicitudDelError.value = null;
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
      solicitudDelError.value = solicitud.outcome_request_id;
      return false;
    } finally {
      enviando.value = null;
    }
  }

  function cargar(forzar = false): Promise<void> {
    if (!forzar && cargado.value) return Promise.resolve();
    return pedir();
  }

  /** El mensaje de esa solicitud, si el último fallo fue suyo. */
  function errorDe(solicitud: OutcomeRequestView): string | null {
    return solicitudDelError.value === solicitud.outcome_request_id ? error.value : null;
  }

  return {
    solicitudes,
    cargado,
    error,
    enviando: computed(() => enviando.value),
    pendientesDe,
    errorDe,
    reportar,
    cargar,
  };
}
