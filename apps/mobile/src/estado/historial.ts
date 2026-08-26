/**
 * El historial de días con cuestionario enviado.
 *
 * Sale entero de `GET /v1/children/{child_id}/history?limit=`, que devuelve un
 * día por sesión enviada, del más reciente al más antiguo, y con lo que cada
 * día produjo: episodio, estimación, recomendación y resultado.
 *
 * Dos cosas que hace este módulo y que la API no promete:
 *
 * - **Índice por fecha.** El calendario pregunta por un día concreto.
 * - **Un día, una fila.** Nada impide enviar dos veces el mismo `local_date`, y
 *   entonces la API devuelve dos filas para ese día. Se queda la primera, que
 *   por el orden del endpoint es la del envío más reciente.
 */

import { computed, ref } from "vue";

import type { ChildHistoryDay } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { DIAS_HISTORIAL } from "@/api/config";
import { historialNino } from "@/api/faro";
import { reconciliar } from "@/estado/respuestas";

const dias = ref<readonly ChildHistoryDay[]>([]);
const cargando = ref(false);
const cargado = ref(false);
const error = ref<string | null>(null);
let ninoCargado: string | null = null;

const porFecha = computed(() => {
  const indice = new Map<string, ChildHistoryDay>();
  for (const dia of dias.value) {
    if (!indice.has(dia.local_date)) indice.set(dia.local_date, dia);
  }
  return indice;
});

async function pedir(ninoId: string): Promise<void> {
  cargando.value = true;
  error.value = null;
  try {
    const respuesta = await historialNino(ninoId);
    dias.value = respuesta.days ?? [];
    // El historial manda sobre la copia local: un día guardado aquí que el
    // servidor no devuelve ya no existe, y arrastrarlo enseña respuestas
    // fantasma y apaga las sugerencias del formulario.
    reconciliar(ninoId, {
      conEnvio: new Set(
        dias.value
          .filter((dia) => dia.submission_id !== null && dia.submission_id !== undefined)
          .map((dia) => dia.local_date),
      ),
      completo: dias.value.length < DIAS_HISTORIAL,
    });
    cargado.value = true;
    ninoCargado = ninoId;
  } catch (fallo) {
    error.value = mensajeDeError(fallo);
  } finally {
    cargando.value = false;
  }
}

export function useHistorial() {
  /** Carga el historial de esa persona. Con `forzar`, vuelve a pedirlo. */
  function cargar(ninoId: string, forzar = false): Promise<void> {
    if (!forzar && ninoCargado === ninoId && cargado.value) return Promise.resolve();
    return pedir(ninoId);
  }

  return { dias, porFecha, cargando, cargado, error, cargar };
}
