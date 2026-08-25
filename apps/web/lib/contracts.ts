/**
 * Tipos del contrato de la API v0.3 y su catálogo de campos.
 *
 * PROVISIONAL - PUERTO HACIA P1. `TAREAS P1.1` genera TypeScript/Zod desde la
 * misma fuente que el JSON Schema. Cuando esos artefactos existan, este archivo
 * se reemplaza por un re-export de `packages/shared/generated`, sin tocar
 * componentes ni páginas. La UI nunca mantiene un contrato paralelo a mano más
 * allá de este punto de sustitución.
 */

export type Source = "home" | "therapy" | "school";
export type SessionKind = "caregiver_daily" | "professional_observation";
export type AnswerInteraction = "manual" | "accept_default" | "edit_default" | "unknown";
export type OutcomeValue = "yes" | "no" | "unknown";
export type ResolutionStatus = "pending" | "yes" | "no" | "unknown" | "conflicted";
export type OutcomeRequestStatus = "open" | "reported" | "conflicted" | "missing";
export type ReviewDecision =
  | "approved"
  | "rejected"
  | "human_plan_substituted"
  | "not_applicable"
  | "deferred";
export type ExecutionStatus = "applied" | "not_applied" | "unknown";
export type FieldType = "float" | "int" | "enum" | "ordinal" | "bool" | "enum_set" | "text";

export interface FieldSpec {
  readonly fieldType: FieldType;
  readonly values?: readonly string[];
  readonly min?: number;
  readonly max?: number;
}

/** SPEC 5.2. Tipo y rango de cada campo diario; la UI no inventa opciones. */
export const FIELD_SPECS: Record<string, FieldSpec> = {
  sleep_hours: { fieldType: "float", min: 0, max: 16 },
  sleep_quality: {
    fieldType: "enum",
    values: ["restorative", "interrupted", "sleep_onset_difficulty", "other"],
  },
  night_awakenings: { fieldType: "int", min: 0, max: 15 },
  wake_state: {
    fieldType: "enum",
    values: ["calm_happy", "tired_sleepy", "irritable_crying", "other"],
  },
  morning_support_need: { fieldType: "ordinal", min: 1, max: 5 },
  gi_status: { fieldType: "enum", values: ["normal", "constipation", "diarrhea", "other"] },
  medication_adherence: {
    fieldType: "enum",
    values: ["taken", "missed", "not_applicable"],
  },
  food_changes: { fieldType: "bool" },
  routine_changes: { fieldType: "bool" },
  alertness: { fieldType: "enum", values: ["low", "calm", "optimal", "high", "other"] },
  dysregulation_event_count: { fieldType: "int", min: 0, max: 20 },
  daily_regulation_state: {
    fieldType: "enum",
    values: ["excellent", "stable_with_support", "frequent_dysregulation", "other"],
  },
  activity_participation: { fieldType: "ordinal", min: 1, max: 5 },
  social_interactions: { fieldType: "ordinal", min: 1, max: 5 },
  eating_status: { fieldType: "ordinal", min: 1, max: 5 },
  attendance_status: {
    fieldType: "enum",
    values: ["present", "absent", "not_applicable"],
  },
  relevant_event_flag: { fieldType: "bool" },
  behavior_tags: {
    fieldType: "enum_set",
    values: [
      "self_regulation_attempt",
      "sensory_seeking",
      "sensory_avoiding",
      "communication_attempt",
      "routine_disruption",
      "other",
    ],
  },
  notes: { fieldType: "text", max: 500 },
};

export interface DefaultSuggestion {
  presentation_id: string;
  value: unknown;
  candidate_count: number;
  posterior_mean: number;
  lower_bound: number;
  n_observations: number;
  estimator_version: string;
}

export interface PlannedQuestion {
  field_code: string;
  reason: string;
  voi_nats: number | null;
  default: DefaultSuggestion | null;
}

export interface OutcomePendingBlock {
  prediction_episode_id: string;
  question_es: string;
  severity_anchors_es: string[];
  target_end_at: string;
  capture_deadline_at: string;
  status: OutcomeRequestStatus;
}

export interface FormSessionView {
  form_session_id: string;
  subject_id: string;
  source: Source;
  session_kind: SessionKind;
  status: string;
  opened_at: string;
  submitted_at: string | null;
  audit_mode: boolean;
  form_policy_version: string;
  voi_status: string;
  plan_source: string;
  outcome_pending: OutcomePendingBlock | null;
  highlighted: PlannedQuestion[];
  tail: PlannedQuestion[];
  answered_field_codes: string[];
  emergency_notice_es: string;
}

export interface AnswerAcceptedView {
  field_observation_id: string | null;
  field_code: string;
  entry_mode: string;
  session: FormSessionView;
}

export interface SubmitFormSessionView {
  form_session_id: string;
  status:
    | "episode_created"
    | "episode_linked"
    | "target_definition_unavailable"
    | "target_definition_ambiguous";
  submitted_at: string;
  prediction_episode_id: string | null;
  linked_prediction_episode_id: string | null;
  outcome_request_id: string | null;
  recommendation_instance_id: string | null;
  reasons: string[];
  emergency_notice_es: string;
}

export interface PredictionOutputView {
  track_id: string;
  intended_use: string;
  status: "ok" | "abstained" | "unavailable";
  estimate_kind: string;
  probability: number | null;
  simulation_score: number | null;
  interval: [number, number] | null;
  interval_method: string | null;
  abstention_reasons: string[];
  model_version: string;
  input_data_origin: string;
  decision_policy_version: null;
  risk_band: null;
}

export interface PredictionEpisodeView {
  prediction_episode_id: string;
  subject_id: string;
  as_of_at: string;
  prediction_at: string;
  target_start_at: string;
  target_end_at: string;
  capture_deadline_at: string;
  target_definition_version: string;
  outputs: PredictionOutputView[];
  outcome_status: OutcomeRequestStatus | null;
  resolution_status: ResolutionStatus | null;
  emergency_notice_es: string;
}

export interface OutcomeRequestView {
  outcome_request_id: string;
  prediction_episode_id: string;
  subject_id: string;
  subject_label: string;
  question_es: string;
  severity_anchors_es: string[];
  target_start_at: string;
  target_end_at: string;
  capture_deadline_at: string;
  status: OutcomeRequestStatus;
  resolution_status: ResolutionStatus;
}

export interface OutcomeRequestListView {
  items: OutcomeRequestView[];
  emergency_notice_es: string;
}

export interface OutcomeReportResponse {
  report: {
    outcome_report_id: string;
    prediction_episode_id: string;
    value: OutcomeValue;
    occurred_at: string | null;
    reported_at: string;
    timing_status: "early" | "on_time" | "late";
    reporter_role: string;
    target_definition_version: string;
    supersedes_id: string | null;
  };
  resolution: {
    outcome_resolution_id: string;
    status: ResolutionStatus;
    resolved_at: string | null;
    qualifying_report_id: string | null;
    ever_conflicted: boolean;
    resolution_version: number;
  };
  request_status: OutcomeRequestStatus;
}

export interface CitationView {
  citation_id: string;
  claim_id: string;
  locator: string;
  quoted_text: string;
  canonical_url: string;
}

export interface RecommendationItemView {
  item_type: "strategy" | "human_plan";
  review_status: string;
  strategy_version_id: string | null;
  human_plan_version_id: string | null;
  action_text_es: string;
  required_approver_role: string | null;
  allowed_executor_roles: string[];
  citations: CitationView[];
  non_actionable: string | null;
  execution_status: ExecutionStatus | null;
}

export interface RecommendationsView {
  status: "matched" | "awaiting_professional_review" | "abstained";
  recommendation_instance_id: string;
  catalog_version: string | null;
  corpus_version: string | null;
  availability_reason: string;
  reasons: string[];
  items: RecommendationItemView[];
  revision: string;
  emergency_notice_es: string;
}

export interface ScenarioView {
  schema_version: string;
  field_values: Record<string, string>;
  context_tags: string[];
  profile_tags: string[];
  contraindication_tags: string[];
}

export interface RecommendationInstanceSummary {
  recommendation_instance_id: string;
  prediction_episode_id: string;
  subject_id: string;
  subject_label: string;
  created_at: string;
  catalog_version: string | null;
  corpus_version: string | null;
  runtime_status: "matched" | "abstained";
  scenario: ScenarioView | null;
  pending_strategy_version_ids: string[];
  revision: string;
}

export interface RecommendationInboxView {
  items: RecommendationInstanceSummary[];
  emergency_notice_es: string;
}

export interface SubjectView {
  subject_id: string;
  display_label: string;
  cohort_kind: string;
}

export interface SessionContextView {
  actor_id: string;
  display_name: string;
  tenant_id: string;
  roles: string[];
  subjects: SubjectView[];
  deployment_mode: string;
  adapters_source: string;
  emergency_notice_es: string;
}

export interface MetricView {
  name: string;
  estimability: "estimable" | "not_estimable";
  value: number | null;
  interval: [number, number] | null;
  reason: string | null;
}

export interface EvaluationReportView {
  evaluation_report_id: string;
  model_version: string;
  track_id: string;
  model_state: string;
  intended_use: string;
  data_origin: string;
  dataset_sha256: string;
  target_definition_version: string | null;
  protocol_version: string;
  metrics: MetricView[];
  abstention_by_reason: Record<string, number>;
  limitations_es: string[];
  published_at: string | null;
  simulation_only: boolean;
}

export interface ApiErrorBody {
  error: { code: string; message_es: string; request_id: string };
}
