/**
 * Un envoltorio tipado por cada ruta de la API (`apps/api/routes/v1.py`).
 *
 * Están **todas**, tenga o no la interfaz una pantalla que las use: la pantalla
 * Salud hoy solo lee, pero el formulario, la valoración y el reporte de
 * resultado ya tienen su llamada lista y probada por el compilador contra el
 * contrato generado.
 *
 * Ninguna función de aquí sabe de Vue: son promesas. La reactividad la ponen
 * los composables.
 */

import type {
  ChildHistoryResponse,
  ChildListResponse,
  ChildView,
  FeedbackRequest,
  FeedbackResponse,
  FormPlanRequest,
  FormPlanResponse,
  FormSubmissionRequest,
  FormSubmissionResponse,
  OutcomeReportRequest,
  OutcomeReportResponse,
  OutcomeRequestListResponse,
  OutcomeRequestState,
  OutcomeResolutionStatus,
  PredictionEpisodeResponse,
  RecommendationInstanceView,
  RecommendationListResponse,
  TodayRecommendationResponse,
} from "@faro/contract/contract";

import { DIAS_HISTORIAL, ORIGEN_API } from "@/api/config";
import { pedir } from "@/api/http";

/**
 * Las dos respuestas que el generador no publica: el backend las declara en
 * `apps/api/contracts/models.py` extendiendo un modelo del contrato con campos
 * que solo existen en la vista HTTP.
 */
export interface VistaEpisodio extends PredictionEpisodeResponse {
  prediction_at: string;
  outcome_state?: OutcomeRequestState | null;
  resolution_status?: OutcomeResolutionStatus | null;
}

export interface VistaReporteResultado extends OutcomeReportResponse {
  request_state: OutcomeRequestState;
}

export interface EstadoServicio {
  status: string;
  spec_version: string;
  mode: string;
  adapters: string;
}

/* Niños ------------------------------------------------------------------- */

export function listarNinos(signal?: AbortSignal): Promise<ChildListResponse> {
  return pedir("/children", { signal });
}

export function obtenerNino(idNino: string, signal?: AbortSignal): Promise<ChildView> {
  return pedir(`/children/${encodeURIComponent(idNino)}`, { signal });
}

export function historialNino(
  idNino: string,
  opciones: { limite?: number; signal?: AbortSignal } = {},
): Promise<ChildHistoryResponse> {
  return pedir(`/children/${encodeURIComponent(idNino)}/history`, {
    consulta: { limit: opciones.limite ?? DIAS_HISTORIAL },
    signal: opciones.signal,
  });
}

/* Formulario diario ------------------------------------------------------- */

/**
 * El plan del formulario de hoy: qué preguntar, en qué orden y qué destacar.
 *
 * Es `POST` porque el plan depende de lo ya respondido, pero no escribe nada.
 */
export function planFormulario(
  idNino: string,
  peticion: FormPlanRequest,
  signal?: AbortSignal,
): Promise<FormPlanResponse> {
  return pedir(`/children/${encodeURIComponent(idNino)}/form-plan`, {
    metodo: "POST",
    cuerpo: peticion,
    signal,
  });
}

/**
 * Envía el formulario del día.
 *
 * La respuesta trae el episodio recién creado y, si hay recomendación en
 * camino, su identificador: el RAG corre después, en segundo plano, y avisa por
 * el WebSocket (`conectarEventos`).
 */
export function enviarFormulario(
  idNino: string,
  peticion: FormSubmissionRequest,
  signal?: AbortSignal,
): Promise<FormSubmissionResponse> {
  return pedir(`/children/${encodeURIComponent(idNino)}/forms`, {
    metodo: "POST",
    cuerpo: peticion,
    signal,
  });
}

/* Episodios de predicción ------------------------------------------------- */

export function obtenerEpisodio(idEpisodio: string, signal?: AbortSignal): Promise<VistaEpisodio> {
  return pedir(`/prediction-episodes/${encodeURIComponent(idEpisodio)}`, { signal });
}

export function recomendacionDeEpisodio(
  idEpisodio: string,
  signal?: AbortSignal,
): Promise<RecommendationInstanceView> {
  return pedir(`/prediction-episodes/${encodeURIComponent(idEpisodio)}/recommendations`, {
    signal,
  });
}

/* Resultados -------------------------------------------------------------- */

export function listarSolicitudesDeResultado(
  signal?: AbortSignal,
): Promise<OutcomeRequestListResponse> {
  return pedir("/outcome-requests", { signal });
}

export function reportarResultado(
  idEpisodio: string,
  peticion: OutcomeReportRequest,
  signal?: AbortSignal,
): Promise<VistaReporteResultado> {
  return pedir(`/prediction-episodes/${encodeURIComponent(idEpisodio)}/outcome-reports`, {
    metodo: "POST",
    cuerpo: peticion,
    signal,
  });
}

/* Recomendaciones --------------------------------------------------------- */

/**
 * La recomendación de hoy, resuelta por el servidor.
 *
 * `status` distingue los cuatro casos que la pantalla tiene que saber
 * diferenciar: sin formulario, redactándose, lista o abstenida. La abstención
 * llega como 200 con `abstention_reason`, nunca como error (SPEC 11.7).
 */
export function recomendacionDeHoy(
  idNino: string,
  signal?: AbortSignal,
): Promise<TodayRecommendationResponse> {
  return pedir(`/children/${encodeURIComponent(idNino)}/recommendations/today`, { signal });
}

export function listarRecomendaciones(
  opciones: {
    estado?: "pending" | "matched" | "abstained";
    idNino?: string;
    limite?: number;
    signal?: AbortSignal;
  } = {},
): Promise<RecommendationListResponse> {
  return pedir("/recommendations", {
    consulta: { status: opciones.estado, child_id: opciones.idNino, limit: opciones.limite },
    signal: opciones.signal,
  });
}

/**
 * Valora una recomendación.
 *
 * `bad` no solo se guarda: dispara una nueva redacción en segundo plano, que
 * llega por el WebSocket como `recommendation.redrafted`.
 */
export function valorarRecomendacion(
  idRecomendacion: string,
  peticion: FeedbackRequest,
  signal?: AbortSignal,
): Promise<FeedbackResponse> {
  return pedir(`/recommendations/${encodeURIComponent(idRecomendacion)}/feedback`, {
    metodo: "POST",
    cuerpo: peticion,
    signal,
  });
}

/* Servicio ---------------------------------------------------------------- */

/** `GET /health` vive fuera del prefijo `/v1`, así que no pasa por `pedir`. */
export async function estadoServicio(signal?: AbortSignal): Promise<EstadoServicio> {
  const respuesta = await fetch(`${ORIGEN_API}/health`, { signal });
  return (await respuesta.json()) as EstadoServicio;
}
