/**
 * La pregunta de cierre: ¿hubo un evento de desregulación?
 *
 * Es la mitad del ciclo que hace que la aplicación aprenda. Un cuestionario
 * abre un episodio —"¿habrá una desregulación en las próximas 24 h?"— y hasta
 * que no se contesta, el baseline personal se queda sin resultados verificados
 * y el modelo no da cifra nunca.
 *
 * Se ofrecen **todas las que están abiertas**, y desde que se abren.
 *
 * Estuvo al revés: se guardaba hasta que la ventana de 24 h cerrara, con el
 * argumento de que antes de eso un "no" no resolvía y dejaba "sí, ocurrió"
 * como única salida real. Ese argumento ya no se sostiene —el backend resuelve
 * un `no` en cuanto se da, aunque llegue `early`— y lo que quedaba era una
 * tarjeta que no aparecía hasta el día siguiente de rellenar el cuestionario:
 * quien acababa de registrar el día no veía nada, y quien se había saltado
 * contestar la de ayer tampoco tenía dónde hacerlo mientras hubiera otra por
 * delante.
 *
 * Lo que sigue mandando es el plazo. Pasado el vencimiento de captura el
 * reporte se guarda pero **no resuelve**, así que un botón ahí produce un envío
 * que parece funcionar y no cuenta para nada. La API ya no las devuelve, pero
 * la lista se pide una vez y se queda en memoria: si la pantalla lleva horas
 * abierta, el filtro es lo único que impide ofrecer una pregunta ya vencida.
 */

import { computed } from "vue";

import type { OutcomeRequestView } from "@/api/contrato";
import { useNino } from "@/estado/nino";
import { useResultados } from "@/estado/resultados";

/** ¿Sigue habiendo plazo para contestar? Fuera de él el reporte ya no resuelve. */
export function enPlazo(solicitud: OutcomeRequestView, ahora = new Date()): boolean {
  return ahora.getTime() < Date.parse(solicitud.capture_deadline_at);
}

/**
 * ¿Se puede contestar esta pregunta ahora mismo?
 *
 * Se exporta suelta para poder probarla sin montar nada, y porque es la única
 * línea que hay que tocar si algún día se decide volver a esperar a que la
 * ventana cierre.
 */
export function sePuedeContestar(
  solicitud: OutcomeRequestView | null,
  ahora = new Date(),
): solicitud is OutcomeRequestView {
  if (solicitud === null) return false;
  return enPlazo(solicitud, ahora);
}

export function useDesregulacion() {
  const { ninoId } = useNino();
  const { error, enviando, pendientesDe, errorDe, reportar, cargar } = useResultados();

  /**
   * Las preguntas que hay que contestar, de la más antigua a la más nueva.
   *
   * Al reportar una, la lista se vuelve a pedir, esa solicitud deja de estar
   * `open` y desaparece de aquí sola: no hace falta recordar aparte cuáles ya
   * se contestaron.
   */
  const pendientes = computed(() =>
    pendientesDe(ninoId.value).filter((solicitud) => sePuedeContestar(solicitud)),
  );

  /** La que se está enviando, para apagar los botones solo mientras dura. */
  const enviandoId = computed(() => enviando.value);

  /** Contesta una de las preguntas abiertas. */
  async function responder(solicitud: OutcomeRequestView, valor: "yes" | "no"): Promise<boolean> {
    return reportar(solicitud, valor);
  }

  return {
    pendientes,
    enviandoId,
    error,
    errorDe,
    responder,
    cargar,
  };
}
