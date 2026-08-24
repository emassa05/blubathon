from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from ml.engine.decision import (
    abstention_reasons,
    build_risk_response,
    confidence_label,
    risk_band,
)
from ml.errors import ContractViolationError
from packages.shared import RiskResponse

CHILD_ID = "e7cd1d03-e4c7-4908-8c52-b612cf1d9584"
PREDICTION_DATE = date(2026, 8, 25)
GENERATED_AT = datetime(2026, 8, 24, 22, 0, tzinfo=UTC)
REQUESTED = [
    {
        "variable": "gi_status",
        "prompt_es": "¿Tuvo molestias digestivas hoy?",
        "voi": 0.12,
    }
]


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.1499, "verde"),
        (0.15, "ambar"),
        (0.3499, "ambar"),
        (0.35, "rojo"),
    ],
)
def test_risk_band_exact_edges(probability: float, expected: str) -> None:
    assert risk_band(probability) == expected


@pytest.mark.parametrize(
    ("icd", "width", "expected"),
    [
        (0.70, 0.25, "alta"),
        (0.70, 0.26, "media"),
        (0.45, 0.45, "media"),
        (0.44, 0.20, "baja"),
        (0.80, 0.46, "baja"),
    ],
)
def test_confidence_table(icd: float, width: float, expected: str) -> None:
    assert confidence_label(icd, width) == expected


def test_each_abstention_condition_is_independent() -> None:
    assert abstention_reasons(0.34, 0.20, 10) == ("low_icd",)
    assert abstention_reasons(0.50, 0.61, 10) == ("wide_interval",)
    assert abstention_reasons(0.50, 0.20, 4) == ("short_history",)


def test_abstention_boundaries_are_inclusive_on_valid_side() -> None:
    assert abstention_reasons(0.35, 0.60, 5) == ()


def test_all_abstention_conditions_can_coexist() -> None:
    assert abstention_reasons(0.10, 0.80, 2) == (
        "low_icd",
        "wide_interval",
        "short_history",
    )


def test_abstention_is_valid_risk_response() -> None:
    response = build_risk_response(
        child_id=CHILD_ID,
        prediction_date=PREDICTION_DATE,
        probability=0.62,
        interval=(0.20, 0.90),
        icd=0.71,
        history_days=10,
        requested_variables=REQUESTED,
        generated_at=GENERATED_AT,
    )
    assert isinstance(response, RiskResponse)
    assert response.status == "insufficient_data"
    assert response.risk is None
    assert response.risk_band is None
    assert response.interval is None
    assert response.confidence is None
    assert response.requested_variables


def test_non_abstaining_response_rounds_and_validates() -> None:
    response = build_risk_response(
        child_id=CHILD_ID,
        prediction_date=PREDICTION_DATE,
        probability=0.623456,
        interval=(0.481234, 0.761234),
        icd=0.71,
        history_days=10,
        requested_variables=REQUESTED,
        generated_at=GENERATED_AT,
    )
    assert response.status == "ok"
    assert response.risk == 0.6235
    assert response.risk_band == "rojo"
    assert response.interval == (0.4812, 0.7612)
    assert response.confidence == "media"


def test_abstention_never_fabricates_requested_variables() -> None:
    with pytest.raises(ContractViolationError, match="at least one"):
        build_risk_response(
            child_id=CHILD_ID,
            prediction_date=PREDICTION_DATE,
            probability=0.20,
            interval=(0.10, 0.20),
            icd=0.20,
            history_days=2,
            requested_variables=[],
            generated_at=GENERATED_AT,
        )


def test_invalid_probability_is_rejected() -> None:
    with pytest.raises(ContractViolationError):
        risk_band(1.1)
