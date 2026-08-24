from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.engine.baseline import predict_baseline
from ml.spec_constants import (
    ABSTAIN_ICD,
    ABSTAIN_MIN_HISTORY_DAYS,
    ABSTAIN_WIDTH,
    BAND_AMBER,
    BAND_RED,
    PROVENANCE_WEIGHTS,
    RANDOM_SEED,
    SYNTH_COEFFICIENTS,
    SYNTH_DAYS,
    SYNTH_N_CHILDREN,
    VOI_KAPPA,
    VOI_SAMPLES,
)
from packages.shared import DailyLog, ExplainResponse, RiskResponse, VoIResponse

FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_fixed_constants_match_spec() -> None:
    assert RANDOM_SEED == 42
    assert (BAND_AMBER, BAND_RED) == (0.15, 0.35)
    assert (ABSTAIN_ICD, ABSTAIN_WIDTH, ABSTAIN_MIN_HISTORY_DAYS) == (0.35, 0.60, 5)
    assert (VOI_SAMPLES, VOI_KAPPA) == (20, 0.15)
    assert (SYNTH_N_CHILDREN, SYNTH_DAYS) == (200, 180)
    assert PROVENANCE_WEIGHTS == {
        "observed": 1.0,
        "confirmed": 1.0,
        "assumed_stable": 0.5,
        "unknown": 0.0,
    }
    assert SYNTH_COEFFICIENTS == {
        "intercept": -2.20,
        "sleep": 0.90,
        "awakenings": 0.50,
        "gi": 0.60,
        "routine": 0.60,
        "sensory": 0.40,
        "sleep_routine": 0.50,
        "gi_sensory": 0.35,
        "carryover": 0.30,
    }


def test_daily_log_validates_literal_spec_example() -> None:
    example = {
        "log_id": "cfe4bc68-82a9-4d29-a240-b59e25b41d0a",
        "child_id": "e7cd1d03-e4c7-4908-8c52-b612cf1d9584",
        "date": "2026-08-25",
        "source": "home",
        "sleep_hours": 6.5,
        "sleep_quality": 2,
        "night_awakenings": 3,
        "wake_state": 2,
        "morning_support_need": 4,
        "gi_status": None,
        "food_changes": False,
        "routine_changes": True,
        "observed_behavior_tags": ["irritable"],
        "observed_behavior_note": None,
        "alertness": 4,
        "dysregulation_events": 2,
        "activity_participation": 3,
        "social_interactions": 2,
        "eating_status": 2,
        "relevant_event_flag": False,
        "relevant_events_note": None,
        "crisis_occurred": False,
        "other_notes": None,
        "capture_method": "form",
        "field_provenance": {
            "sleep_hours": "confirmed",
            "sleep_quality": "observed",
            "night_awakenings": "observed",
            "routine_changes": "observed",
            "gi_status": "assumed_stable",
        },
        "created_at": "2026-08-25T07:12:00Z",
    }
    assert DailyLog.model_validate(example).date.isoformat() == example["date"]


def test_risk_response_validates_literal_spec_example() -> None:
    example = {
        "child_id": "e7cd1d03-e4c7-4908-8c52-b612cf1d9584",
        "date": "2026-08-25",
        "status": "ok",
        "risk": 0.62,
        "risk_band": "rojo",
        "interval": [0.48, 0.76],
        "confidence": "media",
        "icd": 0.71,
        "requested_variables": [
            {"variable": "gi_status", "prompt_es": "¿Tuvo molestias digestivas hoy?", "voi": 0.12}
        ],
        "model_version": "faro-0.2.0",
        "generated_at": "2026-08-25T07:00:00Z",
    }
    assert RiskResponse.model_validate(example).risk == example["risk"]


def test_voi_response_validates_literal_spec_example() -> None:
    example = {
        "child_id": "e7cd1d03-e4c7-4908-8c52-b612cf1d9584",
        "date": "2026-08-25",
        "highlighted": [
            {
                "variable": "sleep_hours",
                "prompt_es": "¿Cuántas horas durmió anoche?",
                "voi": 0.1421,
                "reason": "voi",
                "suggestion": 8.2,
                "suggestion_label_es": None,
            },
            {
                "variable": "gi_status",
                "prompt_es": "¿Tuvo molestias digestivas hoy?",
                "voi": 0.0089,
                "reason": "staleness",
                "days_since_observed": 7,
                "suggestion": 4,
                "suggestion_label_es": "Bien",
            },
        ],
        "filter_question_es": "¿Hoy pasó algo distinto o fuera de lo común?",
        "tail": [
            {
                "variable": "social_interactions",
                "prompt_es": "¿Cómo fueron sus interacciones sociales?",
                "voi": 0.0031,
                "reason": "voi",
                "suggestion": 3,
                "suggestion_label_es": "Neutras",
            }
        ],
    }
    assert len(VoIResponse.model_validate(example).highlighted) == 2


def test_explain_response_validates_literal_spec_example() -> None:
    example = {
        "drivers": [
            {
                "variable": "sleep_hours",
                "shap": -0.31,
                "direction": "empeora",
                "detail_es": "3 noches bajo su normal",
            }
        ],
        "narrative": {
            "headline_es": "Riesgo elevado para mañana",
            "explanation_es": "El sueño reciente está bajo su patrón habitual.",
            "actions_es": ["Proteger la rutina de sueño"],
        },
        "narrative_source": "llm",
        "strategies": [{"id": "advance_sleep", "label_es": "Proteger el sueño"}],
    }
    assert ExplainResponse.model_validate(example).narrative_source == "llm"


@pytest.mark.parametrize(
    "fixture_name",
    ["calm_child.json", "high_risk_child.json", "abstention_child.json"],
)
def test_fixture_histories_validate(fixture_name: str) -> None:
    records = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    logs = [DailyLog.model_validate(record) for record in records]
    assert logs
    assert len({log.child_id for log in logs}) == 1


def test_baseline_changes_with_sleep_hours() -> None:
    rested = predict_baseline({"sleep_hours": 9.0})
    sleep_deprived = predict_baseline({"sleep_hours": 4.0})
    assert sleep_deprived > rested
