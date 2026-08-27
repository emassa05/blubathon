"""Render fictional examples for the published Blubathon v0.4 contract."""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.shared.constants import CONTRACT_VERSION
from packages.shared.schema.registry import PUBLISHED_MODELS

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "packages" / "shared" / "examples"
NAMESPACE = uuid.UUID("6f1f5f2a-1c9e-4c2b-9f2f-2b7a5c9d1e00")
NOW = datetime(2026, 8, 25, 19, 55, tzinfo=UTC)


def ident(label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, label))


def stamp() -> str:
    return f"{NOW.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"


def valid_examples() -> dict[str, tuple[str, dict[str, Any]]]:
    child_id = ident("child")
    episode_id = ident("episode")
    recommendation_id = ident("recommendation")
    citation = {
        "document_title_es": "Guía ficticia de apoyo",
        "locator": "p. 4",
        "quote_es": "Mantener una rutina predecible puede facilitar las transiciones.",
    }
    return {
        "child.list.json": (
            "ChildListResponse",
            {"children": [{"child_id": child_id, "display_label": "Niño demo"}]},
        ),
        "form_plan.request.json": (
            "FormPlanRequest",
            {"source": "caregiver_daily", "answers": {"sleep_quality": "interrupted"}},
        ),
        "form_plan.response.json": (
            "FormPlanResponse",
            {
                "questions": [
                    {
                        "field_code": "routine_changes",
                        "highlighted": True,
                        "reason": "staleness",
                        "voi_nats": None,
                    }
                ],
                "defaults": [],
                "voi_status": "unavailable_model",
                "coverage": 0.62,
            },
        ),
        "form_submission.request.json": (
            "FormSubmissionRequest",
            {
                "source": "caregiver_daily",
                "local_date": "2026-08-25",
                "answers": [
                    {
                        "field_code": "sleep_quality",
                        "value": "interrupted",
                        "interaction": "manual",
                    }
                ],
            },
        ),
        "form_submission.response.json": (
            "FormSubmissionResponse",
            {
                "submission_id": ident("submission"),
                "status": "episode_created",
                "prediction_episode_id": episode_id,
                "recommendation_instance_id": recommendation_id,
                "outcome_request_id": ident("outcome-request"),
            },
        ),
        "recommendation.matched.json": (
            "RecommendationInstanceView",
            {
                "recommendation_instance_id": recommendation_id,
                "child_id": child_id,
                "prediction_episode_id": episode_id,
                "created_at": stamp(),
                "risk_band": "high",
                "query_es": "Riesgo alto. Calidad del sueño : Interrumpido",
                "status": "matched",
                "action_text_es": "Anticipa la siguiente actividad con una señal breve.",
                "purpose_es": "Facilitar una transición predecible.",
                "citations": [citation],
                "attempt": 1,
            },
        ),
        "recommendation.abstained.json": (
            "RecommendationInstanceView",
            {
                "recommendation_instance_id": recommendation_id,
                "child_id": child_id,
                "prediction_episode_id": episode_id,
                "created_at": stamp(),
                "risk_band": "unknown",
                "query_es": "Calidad del sueño : Interrumpido",
                "status": "abstained",
                "citations": [],
                "abstention_reason": "no_indexed_match",
                "attempt": 1,
            },
        ),
        "recommendation.today.json": (
            "TodayRecommendationResponse",
            {
                "status": "matched",
                "risk_band": "high",
                "recommendation_instance_id": recommendation_id,
                "action_text_es": "Anticipa la siguiente actividad con una señal breve.",
                "purpose_es": "Facilitar una transición predecible.",
                "citations": [citation],
                "rating": None,
            },
        ),
        "feedback.request.json": (
            "FeedbackRequest",
            {"rating": "good", "note_es": None},
        ),
        "notification.ready.json": (
            "NotificationEvent",
            {
                "type": "recommendation.ready",
                "child_id": child_id,
                "prediction_episode_id": episode_id,
                "recommendation_instance_id": recommendation_id,
                "status": "matched",
                "abstention_reason": None,
                "at": stamp(),
            },
        ),
    }


def invalid_examples() -> dict[str, tuple[str, str, dict[str, Any]]]:
    return {
        "form_submission.unknown_with_value.invalid.json": (
            "FormSubmissionRequest",
            "An unknown answer cannot carry a value",
            {
                "source": "caregiver_daily",
                "local_date": "2026-08-25",
                "answers": [
                    {
                        "field_code": "sleep_quality",
                        "value": "interrupted",
                        "interaction": "unknown",
                    }
                ],
            },
        ),
        "recommendation.abstained_with_text.invalid.json": (
            "RecommendationInstanceView",
            "An abstention cannot expose an ungrounded draft",
            {
                "recommendation_instance_id": ident("recommendation"),
                "child_id": ident("child"),
                "prediction_episode_id": ident("episode"),
                "created_at": stamp(),
                "risk_band": "unknown",
                "query_es": "Consulta ficticia",
                "status": "abstained",
                "action_text_es": "Texto no permitido",
                "abstention_reason": "draft_not_grounded",
                "attempt": 1,
            },
        ),
        "form_submission.created_without_resources.invalid.json": (
            "FormSubmissionResponse",
            "An episode_created response names every created resource",
            {"submission_id": ident("submission"), "status": "episode_created"},
        ),
    }


def render() -> dict[str, str]:
    files: dict[str, str] = {}
    index: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "generated_by": "python -m tools.contracts.examples",
        "note": "Fictional payloads only.",
        "valid": [],
        "invalid": [],
    }
    for filename, (model_name, payload) in sorted(valid_examples().items()):
        PUBLISHED_MODELS[model_name].model_validate(payload)
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
    expected = {output_dir / relative for relative in files}
    for parent in (output_dir / "valid", output_dir / "invalid"):
        for path in parent.glob("*.json"):
            if path not in expected:
                path.unlink()
    for relative, content in files.items():
        path = output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Blubathon v0.4 examples.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    files = write(args.output_dir)
    valid = sum(name.startswith("valid/") for name in files)
    invalid = sum(name.startswith("invalid/") for name in files)
    print(f"wrote {valid} valid and {invalid} invalid examples to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
