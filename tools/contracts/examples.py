"""Render the handoff examples of TAREAS M1/P1.2.

Valid examples are built from the models themselves, so a published example can
never drift from the published contract. Invalid examples are hand-written
payloads that must fail, each one naming the rule it violates: a contract is only
as clear as the things it refuses.

None of these payloads describes a real person, a real source or a real
approval. `recommendation.match.json` shows the *shape* of a citation using a
demo fixture; it does not assert a clinical source.

    python -m tools.contracts.examples
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.shared.constants import (
    CONTRACT_VERSION,
    DEFAULTS_ESTIMATOR_VERSION,
    FORM_POLICY_VERSION,
)
from packages.shared.schema.registry import PUBLISHED_MODELS

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "packages" / "shared" / "examples"

NAMESPACE = uuid.UUID("6f1f5f2a-1c9e-4c2b-9f2f-2b7a5c9d1e00")
NOW = datetime(2026, 8, 25, 19, 55, tzinfo=UTC)


def ident(label: str) -> str:
    raw = bytearray(uuid.uuid5(NAMESPACE, label).bytes)
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def stamp(offset_hours: float = 0.0) -> str:
    moment = NOW + timedelta(hours=offset_hours)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"


# --------------------------------------------------------------------------
# Valid examples
# --------------------------------------------------------------------------


def _session_base(audit_mode: bool) -> dict[str, Any]:
    return {
        "form_session_id": ident("session"),
        "subject_id": ident("subject"),
        "source": "home",
        "session_kind": "caregiver_daily",
        "opened_at": stamp(),
        "audit_mode": audit_mode,
        "form_policy_version": FORM_POLICY_VERSION,
        "voi_status": "unavailable_model",
    }


def _default_suggestion() -> dict[str, Any]:
    return {
        "presentation_id": ident("presentation"),
        "value": False,
        "candidate_count": 36,
        "posterior_mean": 0.8409,
        "lower_bound": 0.7431,
        "n_observations": 42,
        "estimator_version": DEFAULTS_ESTIMATOR_VERSION,
    }


def _question(
    field_code: str, reason: str, default: dict[str, Any] | None = None
) -> dict[str, Any]:
    question: dict[str, Any] = {"field_code": field_code, "reason": reason, "voi_nats": None}
    if default is not None:
        question["default"] = default
    return question


def _outcome_response(
    *,
    value: str,
    reported_offset: float,
    occurred_offset: float | None,
    timing_status: str,
    resolution_status: str,
    resolved_offset: float | None,
    qualifying: bool,
    ever_conflicted: bool = False,
    resolution_version: int = 1,
) -> dict[str, Any]:
    report_id = ident(f"report-{value}-{timing_status}")
    return {
        "report": {
            "outcome_report_id": report_id,
            "prediction_episode_id": ident("episode"),
            "value": value,
            "occurred_at": None if occurred_offset is None else stamp(occurred_offset),
            "reported_at": stamp(reported_offset),
            "timing_status": timing_status,
            "reporter_role": "caregiver",
            "intake_channel": "form",
            "target_definition_version": "target-demo-1",
        },
        "resolution": {
            "status": resolution_status,
            "resolved_at": None if resolved_offset is None else stamp(resolved_offset),
            "qualifying_report_id": report_id if qualifying else None,
            "ever_conflicted": ever_conflicted,
            "resolution_version": resolution_version,
        },
    }


def valid_examples() -> dict[str, tuple[str, dict[str, Any]]]:
    """filename -> (published model name, payload)."""

    episode_view = {
        "prediction_episode_id": ident("episode"),
        "subject_id": ident("subject"),
        "as_of_at": stamp(),
        "target_start_at": stamp(),
        "target_end_at": stamp(24),
        "capture_deadline_at": stamp(48),
        "target_definition_version": "target-demo-1",
        "decision_policy_version": None,
        "risk_band": None,
    }

    return {
        "form_session.audit.json": (
            "FormSessionResponse",
            {
                **_session_base(audit_mode=True),
                "highlighted": [
                    _question("sleep_quality", "staleness"),
                    _question("food_changes", "canonical_order"),
                ],
                "tail": [_question("notes", "tail")],
            },
        ),
        "form_session.with_default.json": (
            "FormSessionResponse",
            {
                **_session_base(audit_mode=False),
                "highlighted": [
                    _question("sleep_quality", "staleness"),
                    _question("food_changes", "canonical_order", _default_suggestion()),
                ],
                "tail": [_question("notes", "tail")],
            },
        ),
        "form_answer.manual.json": (
            "FormAnswerRequest",
            {
                "answer": {
                    "field_code": "sleep_quality",
                    "interaction": "manual",
                    "value": "interrupted",
                    "default_presentation_id": None,
                }
            },
        ),
        "form_answer.accept_default.json": (
            "FormAnswerRequest",
            {
                "answer": {
                    "field_code": "food_changes",
                    "interaction": "accept_default",
                    "value": False,
                    "default_presentation_id": ident("presentation"),
                }
            },
        ),
        "form_answer.edit_default.json": (
            "FormAnswerRequest",
            {
                "answer": {
                    "field_code": "food_changes",
                    "interaction": "edit_default",
                    "value": True,
                    "default_presentation_id": ident("presentation"),
                }
            },
        ),
        "prediction.synthetic_score.json": (
            "PredictionEpisodeResponse",
            {
                **episode_view,
                "outputs": [
                    {
                        "track_id": "synthetic_reference_v021",
                        "intended_use": "simulation_only",
                        "status": "ok",
                        "estimate_kind": "simulation_score",
                        "probability": None,
                        "simulation_score": 0.42,
                        "interval": None,
                        "interval_method": None,
                        "abstention_reasons": [],
                        "model_version": "synthetic-reference-0.2.1",
                        "input_data_origin": "synthetic",
                    }
                ],
            },
        ),
        "prediction.personal_abstained.json": (
            "PredictionEpisodeResponse",
            {
                **episode_view,
                "outputs": [
                    {
                        "track_id": "real_personal_baseline_v1",
                        "intended_use": "operational_support",
                        "status": "abstained",
                        "estimate_kind": "personal_observed_episode_rate",
                        "probability": None,
                        "simulation_score": None,
                        "interval": None,
                        "interval_method": None,
                        "abstention_reasons": ["insufficient_verified_outcomes"],
                        "model_version": "real-personal-baseline-0.3.0",
                        "input_data_origin": "real",
                    }
                ],
            },
        ),
        "recommendation.match.json": (
            "RecommendationResponse",
            {
                "status": "matched",
                "recommendation_instance_id": ident("instance"),
                "catalog_version": "catalog-demo-1",
                "corpus_version": "corpus-demo-1",
                "items": [
                    {
                        "item_type": "strategy",
                        "strategy_version_id": ident("strategy"),
                        "review_status": "approved",
                        "action_text_es": "Texto exacto revisado de la estrategia de demostración.",
                        "citations": [
                            {
                                "citation_id": ident("citation"),
                                "claim_id": ident("claim"),
                                "locator": "section 2, paragraph 3",
                                "quoted_text": "Fragmento literal verificado de la fixture.",
                                "canonical_url": "https://example.org/versioned-source",
                            }
                        ],
                    }
                ],
                "reasons": [],
            },
        ),
        "recommendation.abstained.json": (
            "RecommendationResponse",
            {
                "status": "abstained",
                "recommendation_instance_id": ident("instance"),
                "catalog_version": None,
                "corpus_version": None,
                "items": [],
                "reasons": ["corpus_not_ready"],
            },
        ),
        "outcome.yes.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="yes",
                reported_offset=20,
                occurred_offset=5,
                timing_status="early",
                resolution_status="yes",
                resolved_offset=20,
                qualifying=True,
            ),
        ),
        "outcome.no.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="no",
                reported_offset=24,
                occurred_offset=None,
                timing_status="on_time",
                resolution_status="no",
                resolved_offset=24,
                qualifying=True,
            ),
        ),
        "outcome.explicit_unknown_pending.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="unknown",
                reported_offset=25,
                occurred_offset=None,
                timing_status="on_time",
                resolution_status="pending",
                resolved_offset=None,
                qualifying=False,
            ),
        ),
        "outcome.early_no_pending.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="no",
                reported_offset=10,
                occurred_offset=None,
                timing_status="early",
                resolution_status="pending",
                resolved_offset=None,
                qualifying=False,
            ),
        ),
        "outcome.conflicted.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="no",
                reported_offset=26,
                occurred_offset=None,
                timing_status="on_time",
                resolution_status="conflicted",
                resolved_offset=None,
                qualifying=False,
                ever_conflicted=True,
                resolution_version=2,
            ),
        ),
        "outcome.late.json": (
            "OutcomeReportResponse",
            _outcome_response(
                value="yes",
                reported_offset=60,
                occurred_offset=5,
                timing_status="late",
                resolution_status="unknown",
                resolved_offset=48,
                qualifying=False,
            ),
        ),
        "recommendation.clinical_review_unavailable.json": (
            "RecommendationResponse",
            {
                "status": "abstained",
                "recommendation_instance_id": ident("recommendation-clinical-review"),
                "catalog_version": None,
                "corpus_version": None,
                "items": [],
                "reasons": ["clinical_review_unavailable"],
            },
        ),
        "evaluation.real_not_estimable.json": (
            "EvaluationResponse",
            {
                "model_version": "real-logit-challenger-0.3.0",
                "track_id": "real_logit_challenger_v1",
                "status": "draft",
                "data_origin": "real",
                "intended_use": "shadow_evaluation",
                "dataset_sha256": "0" * 64,
                "target_definition_version": "target-demo-1",
                "protocol_version": "eval-protocol-0.3.0",
                "metrics": [
                    {
                        "name": "brier_score",
                        "status": "not_estimable",
                        "value": None,
                        "interval": None,
                        "not_estimable_reason": "no_out_of_fold_predictions",
                        "denominator": 0,
                    },
                    {
                        "name": "auc_roc",
                        "status": "not_estimable",
                        "value": None,
                        "interval": None,
                        "not_estimable_reason": "single_class",
                        "denominator": 0,
                    },
                    {
                        "name": "alert_budget_recall",
                        "status": "not_estimable",
                        "value": None,
                        "interval": None,
                        "not_estimable_reason": "no_decision_policy_version",
                        "denominator": None,
                    },
                ],
                "group_metrics": [],
                "source_metrics": [],
                "decision_coverage": {
                    "name": "decision_coverage",
                    "status": "estimated",
                    "value": 0.0,
                    "interval": None,
                    "not_estimable_reason": None,
                    "denominator": 6,
                },
                "abstentions": [
                    {"reason": "insufficient_verified_outcomes", "count": 6, "rate": 1.0}
                ],
                "limitations_es": [
                    "Las tasas se estiman por oportunidad de formulario observada, no como "
                    "incidencia diaria poblacional: completar el formulario puede seleccionar "
                    "los días registrados.",
                    "Resultados de desarrollo fuera de fold. No habilitan el estado "
                    "shadow_evaluated, que exige un periodo prospectivo preregistrado.",
                ],
            },
        ),
        "evaluation.simulation_only.json": (
            "EvaluationResponse",
            {
                "model_version": "synthetic-reference-0.2.1",
                "track_id": "synthetic_reference_v021",
                "status": "published",
                "data_origin": "synthetic",
                "intended_use": "simulation_only",
                "dataset_sha256": "1" * 64,
                "target_definition_version": "target-demo-1",
                "protocol_version": "eval-protocol-0.3.0",
                "metrics": [
                    {
                        "name": "brier_score",
                        "status": "estimated",
                        "value": 0.0812,
                        "interval": {"lower": 0.0614, "upper": 0.1033},
                        "not_estimable_reason": None,
                        "denominator": 420,
                    }
                ],
                "group_metrics": [
                    {
                        "group_kind": "care_mode",
                        "group_value": "standard_support",
                        "subject_count": 0,
                        "positive_count": 0,
                        "negative_count": 0,
                        "suppressed": True,
                        "metrics": [],
                    }
                ],
                "source_metrics": [],
                "decision_coverage": {
                    "name": "decision_coverage",
                    "status": "estimated",
                    "value": 0.87,
                    "interval": None,
                    "not_estimable_reason": None,
                    "denominator": 483,
                },
                "abstentions": [
                    {"reason": "model_artifact_unavailable", "count": 63, "rate": 0.1304}
                ],
                "limitations_es": [
                    "Estas métricas provienen de datos sintéticos (simulation_only). No describen "
                    "el rendimiento con personas reales."
                ],
            },
        ),
        "error.idempotency_conflict.json": (
            "ErrorResponse",
            {
                "error": {
                    "code": "idempotency_conflict",
                    "message_es": "Esa clave de idempotencia ya se usó con un contenido distinto.",
                    "request_id": ident("request-idempotency"),
                }
            },
        ),
        "error.cross_tenant.json": (
            "ErrorResponse",
            {
                "error": {
                    "code": "forbidden",
                    "message_es": "No tienes autorización vigente para esta operación.",
                    "request_id": ident("request-cross-tenant"),
                }
            },
        ),
    }


# --------------------------------------------------------------------------
# Invalid examples
# --------------------------------------------------------------------------


def invalid_examples() -> dict[str, tuple[str, str, dict[str, Any]]]:
    """filename -> (published model name, violated rule, payload)."""

    valid = valid_examples()

    audited_with_default = json.loads(json.dumps(valid["form_session.audit.json"][1]))
    audited_with_default["highlighted"][1]["default"] = _default_suggestion()

    abstained_with_probability = json.loads(
        json.dumps(valid["prediction.personal_abstained.json"][1])
    )
    abstained_with_probability["outputs"][0]["probability"] = 0.19

    simulation_as_probability = json.loads(json.dumps(valid["prediction.synthetic_score.json"][1]))
    simulation_as_probability["outputs"][0]["probability"] = 0.42
    simulation_as_probability["outputs"][0]["simulation_score"] = None

    challenger_exposed = json.loads(json.dumps(valid["prediction.synthetic_score.json"][1]))
    challenger_exposed["outputs"][0] = {
        "track_id": "real_logit_challenger_v1",
        "intended_use": "shadow_evaluation",
        "status": "ok",
        "estimate_kind": "shadow_challenger_score",
        "probability": None,
        "simulation_score": None,
        "interval": None,
        "interval_method": None,
        "abstention_reasons": [],
        "model_version": "real-logit-challenger-0.3.0",
        "input_data_origin": "real",
    }

    abstained_with_items = json.loads(json.dumps(valid["recommendation.abstained.json"][1]))
    abstained_with_items["items"] = valid["recommendation.match.json"][1]["items"]

    human_plan_with_citations = json.loads(json.dumps(valid["recommendation.match.json"][1]))
    human_plan_with_citations["items"][0] = {
        "item_type": "human_plan",
        "human_plan_version_id": ident("plan"),
        "action_text_es": "Plan escrito por la profesional.",
        "citations": valid["recommendation.match.json"][1]["items"][0]["citations"],
    }

    no_with_occurred = json.loads(json.dumps(valid["outcome.no.json"][1]))
    no_with_occurred["report"]["occurred_at"] = stamp(5)

    yes_without_occurred = json.loads(json.dumps(valid["outcome.yes.json"][1]))
    yes_without_occurred["report"]["occurred_at"] = None

    conflicted_not_flagged = json.loads(json.dumps(valid["outcome.conflicted.json"][1]))
    conflicted_not_flagged["resolution"]["ever_conflicted"] = False

    accept_without_presentation = json.loads(
        json.dumps(valid["form_answer.accept_default.json"][1])
    )
    accept_without_presentation["answer"]["default_presentation_id"] = None

    unknown_with_value = json.loads(json.dumps(valid["form_answer.manual.json"][1]))
    unknown_with_value["answer"]["interaction"] = "unknown"

    synthetic_without_label = json.loads(json.dumps(valid["evaluation.simulation_only.json"][1]))
    synthetic_without_label["intended_use"] = "operational_support"

    return {
        "evaluation.synthetic_without_simulation_only.invalid.json": (
            "EvaluationResponse",
            "SPEC 14.3 / INV-34: synthetic metrics are labelled simulation_only",
            synthetic_without_label,
        ),
        "form_session.audited_with_default.invalid.json": (
            "FormSessionResponse",
            "SPEC 6.6 / INV-04: an audited session returns no defaults",
            audited_with_default,
        ),
        "form_answer.accept_default_without_presentation.invalid.json": (
            "FormAnswerRequest",
            "SPEC 5.5 rule 5: accept_default requires the presentation it responds to",
            accept_without_presentation,
        ),
        "form_answer.unknown_with_value.invalid.json": (
            "FormAnswerRequest",
            "SPEC 5.5 rule 3 / CONVENTIONS 8.2: an explicit unknown assigns no value",
            unknown_with_value,
        ),
        "prediction.abstained_with_probability.invalid.json": (
            "PredictionEpisodeResponse",
            "SPEC 11.5 / INV-21: an abstention carries no probability, interval or band",
            abstained_with_probability,
        ),
        "prediction.simulation_as_probability.invalid.json": (
            "PredictionEpisodeResponse",
            "SPEC 2.10 / 8.2: a designed simulation is never labelled a clinical probability",
            simulation_as_probability,
        ),
        "prediction.challenger_exposed.invalid.json": (
            "PredictionEpisodeResponse",
            "SPEC 8.5 / 2.15: the shadow challenger is never exposed in v0.3",
            challenger_exposed,
        ),
        "recommendation.abstained_with_items.invalid.json": (
            "RecommendationResponse",
            "SPEC 11.6: an abstained response returns no items",
            abstained_with_items,
        ),
        "recommendation.human_plan_with_citations.invalid.json": (
            "RecommendationResponse",
            "SPEC 10.2 / INV-29: a human plan does not inherit the RAG citations",
            human_plan_with_citations,
        ),
        "outcome.no_with_occurred_at.invalid.json": (
            "OutcomeReportResponse",
            "SPEC 4.4: only a yes report carries occurred_at",
            no_with_occurred,
        ),
        "outcome.yes_without_occurred_at.invalid.json": (
            "OutcomeReportResponse",
            "SPEC 4.4: a yes report states when the event occurred",
            yes_without_occurred,
        ),
        "outcome.conflicted_not_ever_conflicted.invalid.json": (
            "OutcomeReportResponse",
            "SPEC 4.4: ever_conflicted is monotonic and a conflict sets it",
            conflicted_not_flagged,
        ),
        "submit.target_unavailable_with_episode.invalid.json": (
            "FormSubmitResponse",
            "SPEC 4.2 / INV-13: no target definition means no episode is fabricated",
            {
                "form_session_id": ident("session"),
                "status": "target_definition_unavailable",
                "submitted_at": stamp(),
                "prediction_episode_id": ident("episode"),
                "linked_prediction_episode_id": None,
            },
        ),
        "episode.shifted_window.invalid.json": (
            "PredictionEpisode",
            "SPEC 4.1: the target window is exactly 24 hours after prediction_at",
            {
                "prediction_episode_id": ident("episode"),
                "tenant_id": ident("tenant"),
                "subject_id": ident("subject"),
                "form_session_id": ident("session"),
                "role": "primary",
                "status": "completed",
                "as_of_at": stamp(),
                "prediction_at": stamp(),
                "target_start_at": stamp(),
                "target_end_at": stamp(23),
                "capture_deadline_at": stamp(48),
                "target_definition_version": "target-demo-1",
                "care_mode": "standard_support",
                "profile_version": "profile-1",
                "cohort_kind": "demo_fixture",
                "input_data_origin": "synthetic",
                "feature_snapshot_id": None,
                "created_at": stamp(),
            },
        ),
        "observation.source_not_allowed.invalid.json": (
            "FieldObservation",
            "SPEC 5.4: sleep_hours is reported from home only",
            {
                "tenant_id": ident("tenant"),
                "ingested_at": stamp(),
                "supersedes_id": None,
                "field_observation_id": ident("observation"),
                "subject_id": ident("subject"),
                "form_session_id": ident("session"),
                "field_code": "sleep_hours",
                "value": 8.0,
                "source": "school",
                "actor_id": ident("actor"),
                "entry_mode": "manual_no_default",
                "data_origin": "real",
                "cohort_kind": "real_subject",
                "effective_at": stamp(),
                "local_date": "2026-08-25",
                "source_mapping_id": None,
                "raw_value": None,
            },
        ),
        "scenario.field_outside_allowlist.invalid.json": (
            "ScenarioV1",
            "SPEC 9.7: build_scenario reads only the five allowlisted fields",
            {
                "schema_version": "scenario-1",
                "field_values": {"eating_status": "4"},
                "context_tags": ["therapy"],
                "profile_tags": [],
                "contraindication_tags": [],
            },
        ),
        "idempotency.route_template_path.invalid.json": (
            "IdempotencyScope",
            "SPEC 11.2: the scope uses the concrete path, not the route template",
            {
                "tenant_id": ident("tenant"),
                "actor_id": ident("actor"),
                "method": "POST",
                "normalized_concrete_path": "/api/v1/form-sessions/{id}/answers",
                "idempotency_key": "8f0c6f1e",
            },
        ),
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render() -> dict[str, str]:
    files: dict[str, str] = {}
    index: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "generated_by": "python -m tools.contracts.examples",
        "note": (
            "Fictional payloads. No example asserts a real person, source, licence or "
            "clinical approval."
        ),
        "valid": [],
        "invalid": [],
    }

    for filename, (model_name, payload) in sorted(valid_examples().items()):
        model = PUBLISHED_MODELS[model_name]
        model.model_validate(payload)
        files[f"valid/{filename}"] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        index["valid"].append({"file": f"valid/{filename}", "model": model_name})

    for filename, (model_name, rule, payload) in sorted(invalid_examples().items()):
        files[f"invalid/{filename}"] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        index["invalid"].append(
            {"file": f"invalid/{filename}", "model": model_name, "violates": rule}
        )

    files["index.json"] = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    return files


def write(output_dir: Path = OUTPUT_DIR) -> dict[str, str]:
    files = render()
    for relative, content in files.items():
        path = output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the handoff examples.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    files = write(args.output_dir)
    valid = sum(1 for name in files if name.startswith("valid/"))
    invalid = sum(1 for name in files if name.startswith("invalid/"))
    print(f"wrote {valid} valid and {invalid} invalid examples to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
