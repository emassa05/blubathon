/**
 * Contrato de la API v0.3 para el frontend.
 *
 * Los tipos, los esquemas Zod, las constantes, el catálogo de campos y los
 * textos vienen de `@faro/contract`, que es `packages/shared/generated/index.ts`
 * publicado por H1. Aquí no se redeclara ningún tipo del contrato.
 *
 * Lo único propio son las respuestas de producto que el contrato publicado
 * todavía no cubre. Cada una extiende el tipo de P1 y lleva su solicitud; están
 * en `README.md`, sección "Solicitudes a P1".
 */

export * from "@faro/contract";

import type {
  AnswerSubmission,
  EvaluationResponse,
  ExecutionStatus,
  FieldCode,
  FormSessionResponse,
  FormSessionStatus,
  FormSubmitResponse,
  HumanPlanItem,
  ModelState,
  NonActionableReason,
  OutcomeReportResponse,
  OutcomeRequestState,
  OutcomeResolutionStatus,
  PredictionAbstentionReason,
  PredictionEpisodeResponse,
  RecommendationInboxResponse,
  RecommendationInstanceView,
  RecommendationResponse,
  Role,
  ScenarioV1,
  StrategyItem,
} from "@faro/contract";

import { FARO_FIELD_CATALOG } from "@faro/contract";

/** Solicitud R5: el bloque de outcome pendiente de `SPEC 6.9`, paso 1. */
export interface OutcomePendingBlock {
  prediction_episode_id: string;
  question_es: string;
  severity_anchors_es: string[];
  target_end_at: string;
  capture_deadline_at: string;
  state: OutcomeRequestState;
}

/** Solicitud R5. */
export interface FormSessionView extends FormSessionResponse {
  status: FormSessionStatus;
  submitted_at: string | null;
  plan_source: string;
  outcome_pending: OutcomePendingBlock | null;
  answered_field_codes: FieldCode[];
}

/** Solicitud R12: una corrección enlaza la observación que reemplaza. */
export interface AnswerSubmissionView extends AnswerSubmission {
  effective_at?: string | null;
  supersedes_id?: string | null;
}

/** Solicitud R9: el contrato publica el request, no la respuesta. */
export interface AnswerAcceptedView {
  field_observation_id: string | null;
  field_code: FieldCode;
  entry_mode: string;
  session: FormSessionView;
}

/** Solicitud R1: la causa del cierre sin target no cabe en `SubmitStatus`. */
export interface SubmitFormSessionView extends FormSubmitResponse {
  outcome_request_id: string | null;
  recommendation_instance_id: string | null;
  reasons: PredictionAbstentionReason[];
}

/** Solicitud R10. */
export interface PredictionEpisodeView extends PredictionEpisodeResponse {
  prediction_at: string;
  outcome_state: OutcomeRequestState | null;
  resolution_status: OutcomeResolutionStatus | null;
}

/** Solicitud R8. */
export interface StrategyItemView extends StrategyItem {
  required_approver_role: Role | null;
  allowed_executor_roles: Role[];
  non_actionable: NonActionableReason | null;
  execution_status: ExecutionStatus | null;
}

/** Solicitud R8. */
export interface HumanPlanItemView extends HumanPlanItem {
  strategy_version_id: string | null;
  required_approver_role: Role | null;
  allowed_executor_roles: Role[];
  non_actionable: NonActionableReason | null;
  execution_status: ExecutionStatus | null;
}

export type RecommendationItemView = StrategyItemView | HumanPlanItemView;

/** Solicitud R13: `SPEC 11.2` exige `If-Match` y el contrato no lleva token. */
export interface RecommendationsView extends Omit<RecommendationResponse, "items"> {
  items: RecommendationItemView[];
  revision: string;
}

/** Solicitud R7. */
export interface RecommendationInstanceSummary extends RecommendationInstanceView {
  subject_label: string;
  runtime_status: "matched" | "abstained";
  scenario: ScenarioV1 | null;
  pending_strategy_version_ids: string[];
  revision: string;
}

/** Solicitud R7. */
export interface RecommendationInboxView extends Omit<RecommendationInboxResponse, "items"> {
  items: RecommendationInstanceSummary[];
}

/** Solicitud R14: el estado derivado de la solicitud de outcome (`SPEC 4.4`). */
export interface OutcomeReportResponseView extends OutcomeReportResponse {
  request_state: OutcomeRequestState;
}

/** Solicitud R11. */
export interface EvaluationReportView extends EvaluationResponse {
  evaluation_report_id: string;
  model_state: ModelState;
  published_at: string | null;
}

/** Ruta de soporte fuera de `SPEC 11.1`; P1 no publica un modelo para ella. */
export interface SubjectView {
  subject_id: string;
  display_label: string;
  cohort_kind: string;
}

/** Ruta de soporte fuera de `SPEC 11.1`. */
export interface SessionContextView {
  actor_id: string;
  display_name: string;
  tenant_id: string;
  roles: Role[];
  subjects: SubjectView[];
  deployment_mode: string;
  adapters_source: string;
}

export interface ApiErrorBody {
  error: { code: string; message_es: string; request_id: string };
}

/** Una entrada del catálogo publicado; la UI nunca inventa opciones. */
export type FieldSpec = (typeof FARO_FIELD_CATALOG.fields)[number];

const BY_CODE = new Map<string, FieldSpec>(
  FARO_FIELD_CATALOG.fields.map((spec) => [spec.code, spec]),
);

export function fieldSpec(code: string): FieldSpec | undefined {
  return BY_CODE.get(code);
}

/** El catálogo cerrado de un campo, o `undefined` si el contrato no lo enumera. */
export function allowedValues(spec: FieldSpec): readonly string[] | undefined {
  return "allowedValues" in spec ? spec.allowedValues : undefined;
}

/** `item_type` viaja con un valor por defecto, así que la discriminación usa el
 *  identificador que solo lleva un plan del equipo. */
export function isHumanPlan(item: RecommendationItemView): item is HumanPlanItemView {
  return "human_plan_version_id" in item;
}

/** Un plan del equipo existe porque una review lo sustituyó (`SPEC 10.2`). */
export function reviewStatusOf(item: RecommendationItemView): string {
  return isHumanPlan(item) ? "human_plan_substituted" : item.review_status;
}
