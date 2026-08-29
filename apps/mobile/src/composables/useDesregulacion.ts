/**
 * La pregunta de cierre: ¿hubo un evento de desregulación?
 *
 * Es la mitad del ciclo que hace que la aplicación aprenda. Un cuestionario
 * abre un episodio —"¿habrá una desregulación en las próximas 24 h?"— y hasta
 * que no se contesta, el baseline personal se queda sin resultados verificados
 * y el modelo no da cifra nunca. Por eso deja de ser una tarjeta que se puede
 * pasar por alto y pasa a ser un diálogo obligatorio delante de la pantalla.
 *
 * Ahora bien: obligatorio no puede significar "obligatorio siempre": un `no`
 * solo resuelve si se reporta con la ventana del objetivo ya
 * cerrada. Si el diálogo bloqueara la pantalla mientras la ventana sigue
 * abierta, la única respuesta ofrecible sería "sí, ocurrió", y quien solo
 * quiere ver la pantalla acabaría pulsándola. Eso no es una molestia de
 * interfaz: es un falso positivo escrito en los datos de los que sale la
 * siguiente estimación.
 *
 * De ahí la regla: se bloquea cuando la pregunta se puede contestar de las dos
 * maneras y todavía está en plazo. Mientras tanto sigue estando la tarjeta de
 * siempre, que informa y no exige.
 */

import { computed } from "vue";

import type { OutcomeRequestView } from "@/api/contrato";
import { useNino } from "@/estado/nino";
import { useResultados, ventanaCerrada } from "@/estado/resultados";

/** ¿Sigue habiendo plazo para contestar? Fuera de él el reporte ya no resuelve. */
export function enPlazo(solicitud: OutcomeRequestView, ahora = new Date()): boolean {
  return ahora.getTime() < Date.parse(solicitud.capture_deadline_at);
}

/**
 * ¿Hay que exigir esta respuesta antes de dejar ver la pantalla?
 *
 * Se exporta suelta para poder probarla sin montar nada, y porque es la única
 * línea que hay que tocar si algún día se decide bloquear también con la
 * ventana abierta.
 */
export function exigeRespuesta(
  solicitud: OutcomeRequestView | null,
  ahora = new Date(),
): solicitud is OutcomeRequestView {
  if (solicitud === null) return false;
  return ventanaCerrada(solicitud, ahora) && enPlazo(solicitud, ahora);
}

export function useDesregulacion() {
  const { ninoId } = useNino();
  const { error, enviando, pendienteDe, reportar, cargar } = useResultados();

  /** La solicitud abierta de esa persona, la exija o no. */
  const solicitud = computed(() => pendienteDe(ninoId.value));

  /**
   * La que hay que contestar ahora. Al reportarla, la lista se vuelve a pedir,
   * la solicitud deja de estar `open` y esto pasa a `null` solo: no hace falta
   * recordar aparte que ya se contestó.
   */
  const obligatoria = computed(() => (exigeRespuesta(solicitud.value) ? solicitud.value : null));

  /** La que se enseña como tarjeta: existe, pero todavía no se puede exigir. */
  const informativa = computed(() =>
    solicitud.value !== null && obligatoria.value === null ? solicitud.value : null,
  );

  const bloqueada = computed(() => obligatoria.value !== null);

  /**
   * ¿Resolvería algo un "no ocurrió" ahora mismo?
   *
   * Solo con la ventana de 24 h ya cerrada. Antes de eso el backend **acepta**
   * el reporte —201, `timing_status: "early"`— pero lo deja en `pending` y la
   * solicitud sigue abierta: la tarjeta no se va, la racha no se mueve y no hay
   * ningún error que enseñar. Desde fuera se ve como que el botón no hace nada,
   * que es exactamente lo que hacía.
   *
   * Así que se deja de ofrecer mientras no pueda cumplir. El "sí, ocurrió" sí
   * cuenta desde el primer momento —la ventana empieza en el propio envío—, y
   * ese se sigue pudiendo pulsar.
   */
  const permiteDescartar = computed(
    () => informativa.value !== null && ventanaCerrada(informativa.value),
  );

  /**
   * Contesta la pregunta abierta, la exija el diálogo o la enseñe la tarjeta:
   * solo hay una por persona y es la misma solicitud en los dos sitios.
   */
  async function responder(valor: "yes" | "no"): Promise<boolean> {
    const pendiente = solicitud.value;
    if (pendiente === null) return false;
    // Última defensa: un `no` antes de tiempo se guarda y no resuelve, así que
    // no se manda. La interfaz ya no lo ofrece —ver `permiteDescartar`—; esto
    // es para que no lo pueda mandar nadie por otro camino.
    if (valor === "no" && !ventanaCerrada(pendiente)) return false;
    return reportar(pendiente, valor);
  }

  return {
    solicitud,
    obligatoria,
    informativa,
    bloqueada,
    permiteDescartar,
    error,
    enviando: computed(() => enviando.value !== null),
    responder,
    cargar,
  };
}
