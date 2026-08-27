/**
 * La recomendación de hoy.
 *
 * `GET /v1/children/{child_id}/recommendations/today` responde siempre 200 con
 * un estado explícito: la abstención no es un error y no viaja en el sobre de
 * error. Los cuatro estados son `no_submission_today`, `pending`, `matched` y
 * `abstained`, y solo `matched` trae texto.
 *
 * El día lo pone el servidor, no el cliente: el endpoint no acepta fecha.
 */

import { ref } from "vue";

import type { TodayRecommendationResponse } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { recomendacionDeHoy } from "@/api/blubathon";

const recomendacion = ref<TodayRecommendationResponse | null>(null);
const cargando = ref(false);
const error = ref<string | null>(null);
let ninoCargado: string | null = null;

async function pedir(ninoId: string): Promise<void> {
  cargando.value = true;
  error.value = null;
  try {
    recomendacion.value = await recomendacionDeHoy(ninoId);
    ninoCargado = ninoId;
  } catch (fallo) {
    error.value = mensajeDeError(fallo);
  } finally {
    cargando.value = false;
  }
}

export function useRecomendacionHoy() {
  function cargar(ninoId: string, forzar = false): Promise<void> {
    if (!forzar && ninoCargado === ninoId && recomendacion.value !== null) {
      return Promise.resolve();
    }
    return pedir(ninoId);
  }

  return { recomendacion, cargando, error, cargar };
}
