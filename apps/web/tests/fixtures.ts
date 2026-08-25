/**
 * Respuestas fixture de la API para los tests de UI.
 *
 * Son ficticias y replican la forma exacta del contrato v0.3, no un export real.
 */

import type {
  FormSessionView,
  FormQuestion,
  PredictionOutputView,
  RecommendationsView,
} from "@/lib/contracts";

export function question(overrides: Partial<FormQuestion> = {}): FormQuestion {
  return {
    field_code: "sleep_quality",
    reason: "staleness",
    voi_nats: null,
    default: null,
    ...overrides,
  };
}

export function suggestedQuestion(): FormQuestion {
  return question({
    field_code: "food_changes",
    reason: "canonical_order",
    default: {
      presentation_id: "00000000-0000-4000-8000-000000000701",
      value: false,
      candidate_count: 36,
      posterior_mean: 0.8409,
      lower_bound: 0.7431,
      n_observations: 42,
      estimator_version: "defaults-mock-0.3.0",
    },
  });
}

export function formSession(overrides: Partial<FormSessionView> = {}): FormSessionView {
  return {
    form_session_id: "00000000-0000-4000-8000-000000000801",
    subject_id: "00000000-0000-4000-8000-000000000101",
    source: "home",
    session_kind: "caregiver_daily",
    status: "draft",
    opened_at: "2026-08-25T12:00:00.000Z",
    submitted_at: null,
    audit_mode: false,
    form_policy_version: "form-0.3.0",
    voi_status: "unavailable_model",
    plan_source: "mock",
    outcome_pending: null,
    highlighted: [question(), suggestedQuestion()],
    tail: [question({ field_code: "gi_status", reason: "tail" })],
    answered_field_codes: [],
    ...overrides,
  };
}

export function abstainedBaseline(): PredictionOutputView {
  return {
    track_id: "real_personal_baseline_v1",
    intended_use: "operational_support",
    status: "abstained",
    estimate_kind: "personal_observed_episode_rate",
    probability: null,
    simulation_score: null,
    interval: null,
    interval_method: null,
    abstention_reasons: ["insufficient_verified_outcomes"],
    model_version: "personal-baseline-mock-0.3.0",
    input_data_origin: "synthetic",
  };
}

export function simulationScore(): PredictionOutputView {
  return {
    track_id: "synthetic_reference_v021",
    intended_use: "simulation_only",
    status: "ok",
    estimate_kind: "simulation_score",
    probability: null,
    simulation_score: 0.42,
    interval: null,
    interval_method: null,
    abstention_reasons: [],
    model_version: "synthetic-reference-mock-0.2.1",
    input_data_origin: "synthetic",
  };
}

export function awaitingReview(): RecommendationsView {
  return {
    status: "awaiting_professional_review",
    recommendation_instance_id: "00000000-0000-4000-8000-000000000901",
    catalog_version: "catalog-fixture-0.3.0",
    corpus_version: "corpus-fixture-0.3.0",
    reasons: [],
    items: [],
    revision: "rev-1",
  };
}

export function abstainedRecommendations(): RecommendationsView {
  return {
    ...awaitingReview(),
    status: "abstained",
    catalog_version: null,
    corpus_version: null,
    reasons: ["clinical_review_unavailable"],
  };
}

export function matchedRecommendations(): RecommendationsView {
  return {
    ...awaitingReview(),
    status: "matched",
    items: [
      {
        item_type: "strategy",
        review_status: "approved",
        strategy_version_id: "00000000-0000-4000-8000-000000000601",
        action_text_es: "Revisen luz, ruido y temperatura del lugar donde duerme.",
        required_approver_role: "professional",
        allowed_executor_roles: ["caregiver"],
        citations: [
          {
            citation_id: "00000000-0000-4000-8000-000000000602",
            claim_id: "claim-1",
            locator: "sección 2, párrafo 3",
            quoted_text: "conviene revisar primero las condiciones del entorno",
            canonical_url: "https://example.invalid/faro/fixture-doc-001/v1",
          },
        ],
        non_actionable: null,
        execution_status: null,
      },
      {
        item_type: "human_plan",
        strategy_version_id: null,
        human_plan_version_id: "00000000-0000-4000-8000-000000000603",
        action_text_es: "Acordamos un aviso verbal breve antes de cada cambio.",
        required_approver_role: "professional",
        allowed_executor_roles: ["caregiver"],
        citations: [],
        non_actionable: null,
        execution_status: null,
      },
    ],
  };
}
