"""Deterministic risk bands, confidence, and abstention from SPEC sections 4-6."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from ml.errors import ContractViolationError
from ml.spec_constants import (
    ABSTAIN_ICD,
    ABSTAIN_MIN_HISTORY_DAYS,
    ABSTAIN_WIDTH,
    BAND_AMBER,
    BAND_RED,
    CONFIDENCE_HIGH_ICD,
    CONFIDENCE_HIGH_WIDTH,
    CONFIDENCE_MEDIUM_ICD,
    CONFIDENCE_MEDIUM_WIDTH,
    MODEL_VERSION,
    RISK_API_DECIMALS,
    RISK_MAX,
    RISK_MIN,
    VOI_MAX_REQUESTED_VARIABLES,
)
from packages.shared import RequestedVariable, RiskResponse

RiskBand = Literal["verde", "ambar", "rojo"]
Confidence = Literal["alta", "media", "baja"]
AbstentionReason = Literal["low_icd", "wide_interval", "short_history"]


def risk_band(probability: float) -> RiskBand:
    """Map a canonical probability to the fixed green, amber, or red band."""
    if not RISK_MIN <= probability <= RISK_MAX:
        raise ContractViolationError("risk probability must be between zero and one")
    if probability < BAND_AMBER:
        return "verde"
    if probability < BAND_RED:
        return "ambar"
    return "rojo"


def confidence_label(icd: float, width: float) -> Confidence:
    """Combine data quality and ensemble interval width using SPEC section 5.3."""
    if not RISK_MIN <= icd <= RISK_MAX:
        raise ContractViolationError("ICD must be between zero and one")
    if not RISK_MIN <= width <= RISK_MAX:
        raise ContractViolationError("interval width must be between zero and one")
    if icd >= CONFIDENCE_HIGH_ICD and width <= CONFIDENCE_HIGH_WIDTH:
        return "alta"
    if icd >= CONFIDENCE_MEDIUM_ICD and width <= CONFIDENCE_MEDIUM_WIDTH:
        return "media"
    return "baja"


def abstention_reasons(
    icd: float,
    width: float,
    history_days: int,
) -> tuple[AbstentionReason, ...]:
    """Return every active abstention condition without treating it as an error."""
    reasons: list[AbstentionReason] = []
    if icd < ABSTAIN_ICD:
        reasons.append("low_icd")
    if width > ABSTAIN_WIDTH:
        reasons.append("wide_interval")
    if history_days < ABSTAIN_MIN_HISTORY_DAYS:
        reasons.append("short_history")
    return tuple(reasons)


def _requested_variables(
    requested_variables: Iterable[RequestedVariable | dict[str, object]],
) -> list[RequestedVariable]:
    variables = [
        item if isinstance(item, RequestedVariable) else RequestedVariable.model_validate(item)
        for item in requested_variables
    ]
    if len(variables) > VOI_MAX_REQUESTED_VARIABLES:
        raise ContractViolationError(
            f"requested_variables cannot exceed {VOI_MAX_REQUESTED_VARIABLES} items"
        )
    return variables


def build_risk_response(
    *,
    child_id: str | UUID,
    prediction_date: date,
    probability: float,
    interval: tuple[float, float],
    icd: float,
    history_days: int,
    requested_variables: Iterable[RequestedVariable | dict[str, object]],
    generated_at: datetime | None = None,
    model_version: str = MODEL_VERSION,
) -> RiskResponse:
    """Build the central API contract, including valid HTTP-200 abstention output."""
    if not RISK_MIN <= probability <= RISK_MAX:
        raise ContractViolationError("risk probability must be between zero and one")
    lower, upper = interval
    if not RISK_MIN <= lower <= upper <= RISK_MAX:
        raise ContractViolationError("prediction interval must be ordered within zero and one")
    width = upper - lower
    reasons = abstention_reasons(icd, width, history_days)
    variables = _requested_variables(requested_variables)
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise ContractViolationError("generated_at must use UTC")

    common = {
        "child_id": child_id,
        "date": prediction_date,
        "icd": round(icd, RISK_API_DECIMALS),
        "requested_variables": variables,
        "model_version": model_version,
        "generated_at": timestamp,
    }
    if reasons:
        if not variables:
            raise ContractViolationError("abstention requires at least one requested variable")
        return RiskResponse(
            status="insufficient_data",
            risk=None,
            risk_band=None,
            interval=None,
            confidence=None,
            **common,
        )

    return RiskResponse(
        status="ok",
        risk=round(probability, RISK_API_DECIMALS),
        risk_band=risk_band(probability),
        interval=(
            round(lower, RISK_API_DECIMALS),
            round(upper, RISK_API_DECIMALS),
        ),
        confidence=confidence_label(icd, width),
        **common,
    )
