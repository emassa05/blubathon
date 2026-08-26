import { onScopeDispose, ref, shallowRef, watch, type Ref } from "vue";

import { ID_NINO } from "@/api/config";
import { ErrorFaro } from "@/api/errores";
import { listarNinos } from "@/api/faro";
import { cargarResumenSalud } from "@/adaptadores/resumenSalud";
import type { ResumenSalud } from "@/types/salud";

/**
 * Sin `VITE_FARO_CHILD_ID`, el primero de la lista.
 *
 * La demo es mono-tenant y no tiene selector de niño; preguntarlo es preferible
 * a dejar un UUID de la semilla escrito en el código, que caducaría en cuanto
 * se resembrara la base.
 */
async function resolverNino(signal: AbortSignal): Promise<string> {
  if (ID_NINO) return ID_NINO;
  const primero = (await listarNinos(signal)).children?.[0];
  if (primero === undefined) {
    throw new ErrorFaro({
      codigo: "not_found",
      mensajeEs: "No hay ningún niño registrado en esta cuenta.",
    });
  }
  return primero.child_id;
}

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
export function useResumenSalud(fechaIso: Ref<string>) {
  const resumen = shallowRef<ResumenSalud | null>(null);
  const cargando = ref(true);
  const error = shallowRef<ErrorFaro | null>(null);

  let enCurso: AbortController | null = null;
  let idNino: string | null = null;

  async function cargar(): Promise<void> {
    enCurso?.abort();
    const propio = new AbortController();
    enCurso = propio;

    cargando.value = true;
    error.value = null;

    try {
      idNino ??= await resolverNino(propio.signal);
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
      error.value = fallo instanceof ErrorFaro ? fallo : ErrorFaro.red(fallo);
    } finally {
      if (!propio.signal.aborted) cargando.value = false;
    }
  }

  watch(fechaIso, cargar, { immediate: true });
  onScopeDispose(() => enCurso?.abort());

  return { resumen, cargando, error, recargar: cargar };
}
