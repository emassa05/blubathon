/**
 * Las llamadas de la API v0.4 que esta aplicación usa.
 *
 * Una función por endpoint publicado en `apps/api/routes/v1.py`, con su ruta y
 * su forma tal cual. No hay endpoints nuevos ni parámetros inventados: si algo
 * falta en el contrato, falta en la pantalla, y se anota en `NOTAS-API.md`.
 */

import { peticion } from "@/api/cliente";
import {
  ORIGEN_CUIDADOR,
  type ChildHistoryResponse,
  type ChildListResponse,
  type FieldCode,
  type FormPlanResponse,
  type FormSubmissionRequest,
  type FormSubmissionResponse,
  type TodayRecommendationResponse,
  type ValorCampo,
} from "@/api/contrato";

/** Tope del servidor para `limit` en el historial (`Query(ge=1, le=100)`). */
export const LIMITE_HISTORIAL_MAXIMO = 100;

/** `GET /v1/children` */
export function listarNinos(signal?: AbortSignal): Promise<ChildListResponse> {
  return peticion<ChildListResponse>("/children", { signal });
}

/** `GET /v1/children/{child_id}/history?limit=` */
export function historialDelNino(
  childId: string,
  limite = LIMITE_HISTORIAL_MAXIMO,
  signal?: AbortSignal,
): Promise<ChildHistoryResponse> {
  const ruta = `/children/${encodeURIComponent(childId)}/history?limit=${limite}`;
  return peticion<ChildHistoryResponse>(ruta, { signal });
}

/** `GET /v1/children/{child_id}/recommendations/today` */
export function recomendacionDeHoy(
  childId: string,
  signal?: AbortSignal,
): Promise<TodayRecommendationResponse> {
  const ruta = `/children/${encodeURIComponent(childId)}/recommendations/today`;
  return peticion<TodayRecommendationResponse>(ruta, { signal });
}

/**
 * `POST /v1/children/{child_id}/form-plan`
 *
 * El plan es sin estado: se le mandan las respuestas que ya hay y devuelve qué
 * preguntar primero, qué sugerencias hay y la cobertura. Pedirlo no abre nada
 * ni escribe nada.
 */
export function planDelFormulario(
  childId: string,
  respondidas: Readonly<Partial<Record<FieldCode, ValorCampo>>>,
  signal?: AbortSignal,
): Promise<FormPlanResponse> {
  return peticion<FormPlanResponse>(`/children/${encodeURIComponent(childId)}/form-plan`, {
    metodo: "POST",
    cuerpo: { source: ORIGEN_CUIDADOR, answers: respondidas },
    signal,
  });
}

/**
 * `POST /v1/children/{child_id}/forms`
 *
 * Envía el cuestionario de un día. Responde 201 con el estado del envío: si
 * abrió un episodio, si se enganchó a uno abierto o si no había definición de
 * resultado vigente.
 */
export function enviarFormulario(
  childId: string,
  peticionEnvio: FormSubmissionRequest,
  signal?: AbortSignal,
): Promise<FormSubmissionResponse> {
  return peticion<FormSubmissionResponse>(`/children/${encodeURIComponent(childId)}/forms`, {
    metodo: "POST",
    cuerpo: peticionEnvio,
    signal,
  });
}
