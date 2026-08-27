/**
 * Punto único de entrada del contrato ejecutable.
 *
 * Nada del contrato se declara dos veces: los tipos, el catálogo de campos, los
 * textos visibles y las constantes vienen de `packages/shared/generated`, que se
 * genera desde `packages/shared` y no se escribe a mano. Este módulo solo
 * reexporta lo que la pantalla usa, igual que `apps/api/contracts/models.py`
 * hace del lado del servidor.
 *
 * Se importa por alias (`@contrato/*`, en `vite.config.ts` y `tsconfig.json`) y
 * archivo por archivo: `generated/index.ts` arrastraría `contract.zod.ts`, que
 * depende de Zod, y esta aplicación no tiene dependencias de runtime.
 */

export type {
  AnswerItem,
  ChildHistoryDay,
  ChildHistoryOutcome,
  ChildHistoryPrediction,
  ChildHistoryRecommendation,
  ChildHistoryResponse,
  ChildListItem,
  ChildListResponse,
  DefaultSuggestion,
  ErrorResponse,
  FieldCode,
  FormPlanRequest,
  FormPlanResponse,
  FormQuestion,
  FormSubmissionRequest,
  FormSubmissionResponse,
  OutcomeReportRequest,
  OutcomeReportValue,
  OutcomeRequestListResponse,
  OutcomeRequestView,
  RecommendationCitation,
  TodayRecommendationResponse,
} from "@contrato/contract";

export { BLUBATHON_FIELD_CATALOG } from "@contrato/field-catalog";
export { BLUBATHON_TEXTS_ES } from "@contrato/texts";
export { BLUBATHON_CONSTANTS } from "@contrato/constants";

/** Lo que el cuestionario diario del cuidador declara como origen (SPEC 5.5). */
export const ORIGEN_CUIDADOR = "caregiver_daily" as const;

/** Valor de una respuesta, tal y como viaja en el contrato. */
export type ValorCampo = boolean | number | string | string[];

/** Cómo declara el cliente la interacción; el servidor deriva el `entry_mode`. */
export type Interaccion = "manual" | "accept_default" | "edit_default" | "unknown";
