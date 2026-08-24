"""Fast deterministic comparator for model evaluation and VoI development."""

from __future__ import annotations

import math
from collections.abc import Mapping

from ml.spec_constants import (
    BASELINE_ALERTNESS_OPTIMAL,
    BASELINE_ALERTNESS_SCALE,
    BASELINE_AWAKENINGS_CENTER,
    BASELINE_AWAKENINGS_SCALE,
    BASELINE_GI_RANGE,
    RISK_MAX,
    RISK_MIN,
    SYNTH_COEFFICIENTS,
    SYNTH_SLEEP_NEED_MEAN,
)


def _optional_float(features: Mapping[str, object], name: str, default: float) -> float:
    value = features.get(name)
    if value is None:
        return default
    return float(value)


def predict_baseline(features: Mapping[str, object]) -> float:
    """Apply SPEC section 8.2 coefficients without training a model."""
    sleep_need = _optional_float(features, "sleep_need", SYNTH_SLEEP_NEED_MEAN)
    sleep_hours = _optional_float(features, "sleep_hours", sleep_need)
    sleep_debt = _optional_float(
        features,
        "sleep_debt",
        max(RISK_MIN, sleep_need - sleep_hours) / sleep_need,
    )
    awakenings = _optional_float(features, "night_awakenings", BASELINE_AWAKENINGS_CENTER)
    awakenings_z = _optional_float(
        features,
        "night_awakenings_z",
        (awakenings - BASELINE_AWAKENINGS_CENTER) / BASELINE_AWAKENINGS_SCALE,
    )
    gi_status = _optional_float(features, "gi_status", BASELINE_GI_RANGE + RISK_MAX)
    gi_burden = _optional_float(
        features,
        "gi_burden",
        (BASELINE_GI_RANGE + RISK_MAX - gi_status) / BASELINE_GI_RANGE,
    )
    routine_load = _optional_float(
        features,
        "routine_load",
        float(bool(features.get("routine_changes", False))),
    )
    alertness = _optional_float(features, "alertness", BASELINE_ALERTNESS_OPTIMAL)
    sensory_load = _optional_float(
        features,
        "sensory_load",
        min(RISK_MAX, abs(alertness - BASELINE_ALERTNESS_OPTIMAL) / BASELINE_ALERTNESS_SCALE)
        + float(bool(features.get("relevant_event_flag", False))),
    )

    coefficient = SYNTH_COEFFICIENTS
    score = (
        coefficient["intercept"]
        + coefficient["sleep"] * sleep_debt
        + coefficient["awakenings"] * awakenings_z
        + coefficient["gi"] * gi_burden
        + coefficient["routine"] * routine_load
        + coefficient["sensory"] * sensory_load
        + coefficient["sleep_routine"] * sleep_debt * routine_load
        + coefficient["gi_sensory"] * gi_burden * sensory_load
    )
    probability = RISK_MAX / (RISK_MAX + math.exp(-score))
    return min(RISK_MAX, max(RISK_MIN, probability))
