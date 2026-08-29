/**
 * El resumen del día visible, con sus estados de carga y de error.
 *
 * Cada cambio de día cancela la petición anterior: al pulsar el chevron varias
 * veces seguidas, la respuesta que llegue tarde no puede pisar a la del día que
 * de verdad se está mirando.
 *
 * Al fallar, el resumen se vacía en vez de quedarse con el del día anterior:
 * una cifra de riesgo bajo la fecha equivocada es peor que no mostrar cifra.
 */

import { onScopeDispose, ref, shallowRef, watch, type Ref } from "vue";

import { conectarEventos } from "@/api/eventos";
import { ErrorBlubathon } from "@/api/errores";
import { cargarResumenSalud } from "@/adaptadores/resumenSalud";
import { useNino } from "@/estado/nino";
import type { ResumenSalud } from "@/types/salud";

export function useResumenSalud(fechaIso: Ref<string>) {
  const { ninoId, cargar: cargarNino, error: errorNino } = useNino();
  const resumen = shallowRef<ResumenSalud | null>(null);
  const cargando = ref(true);
  const error = shallowRef<ErrorBlubathon | null>(null);

  let enCurso: AbortController | null = null;

  /**
   * @param silencioso Vuelve a pedir sin encender el estado de carga.
   *
   * Un refresco que nadie pidió no puede vaciar la pantalla. `cargando` tapa las
   * tarjetas con un aviso, y eso es lo correcto cuando alguien acaba de cambiar
   * de día y lo que hay debajo es de otra fecha; cuando lo que ha pasado es que
   * el backend avisó de que la recomendación ya está, la pantalla tiene que
   * seguir donde estaba y cambiar solo lo que cambió.
   */
  async function cargar(silencioso = false): Promise<void> {
    enCurso?.abort();
    const propio = new AbortController();
    enCurso = propio;

    if (!silencioso) cargando.value = true;
    error.value = null;

    try {
      if (ninoId.value === null) await cargarNino();
      if (propio.signal.aborted) return;

      const idNino = ninoId.value;
      if (idNino === null) {
        throw new ErrorBlubathon({
          codigo: "not_found",
          mensajeEs: errorNino.value ?? "No hay ningún niño registrado en esta cuenta.",
        });
      }

      const nuevo = await cargarResumenSalud({
        idNino,
        fechaIso: fechaIso.value,
        signal: propio.signal,
      });
      if (propio.signal.aborted) return;
      resumen.value = nuevo;
    } catch (fallo) {
      if (propio.signal.aborted) return;
      resumen.value = null;
      error.value = fallo instanceof ErrorBlubathon ? fallo : ErrorBlubathon.red(fallo);
    } finally {
      if (!propio.signal.aborted && !silencioso) cargando.value = false;
    }
  }

  /*
   * La recomendación no llega con el resto del día.
   *
   * El RAG corre después de guardar el formulario —recupera fragmentos y redacta
   * encima, y eso tarda lo que tarde el modelo—, así que el `POST` contesta con
   * la recomendación todavía en `pending` y el texto aparece más tarde. Sin
   * esto, "más tarde" significaba "cuando alguien recargue la página": la
   * tarjeta se quedaba con los renglones de espera puestos delante de una
   * recomendación que ya estaba escrita en la base.
   *
   * El backend ya lo avisa por el canal de eventos y nadie escuchaba. Aquí se
   * escucha, y lo que se hace con el aviso es volver a preguntar: el evento dice
   * que algo cambió, no qué dice ahora, y esa sigue siendo la respuesta de la
   * API y no algo que la pantalla pueda armar por su cuenta.
   */
  const cortarEventos = conectarEventos((evento) => {
    if (evento.type === "feedback.recorded") return;
    // `recommendation.redrafted` no dice de quién es, así que solo se filtra lo
    // que se puede filtrar. Preguntar de más cuesta una petición; no preguntar
    // deja la tarjeta mintiendo.
    if (
      evento.type === "recommendation.ready" &&
      ninoId.value !== null &&
      evento.child_id !== ninoId.value
    ) {
      return;
    }
    void cargar(true);
  });

  watch(fechaIso, () => cargar(), { immediate: true });
  onScopeDispose(() => {
    cortarEventos();
    enCurso?.abort();
  });

  return { resumen, cargando, error, recargar: () => cargar() };
}
