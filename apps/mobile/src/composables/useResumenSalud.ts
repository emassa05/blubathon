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

  async function cargar(): Promise<void> {
    enCurso?.abort();
    const propio = new AbortController();
    enCurso = propio;

    cargando.value = true;
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
      if (!propio.signal.aborted) cargando.value = false;
    }
  }

  watch(fechaIso, cargar, { immediate: true });
  onScopeDispose(() => enCurso?.abort());

  return { resumen, cargando, error, recargar: cargar };
}
