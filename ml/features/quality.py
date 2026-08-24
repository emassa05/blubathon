"""Data Quality Index (ICD) from SPEC section 5."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from ml.spec_constants import (
    CATEGORICAL_FIELDS,
    FIELD_RANGES,
    ICD_CONSISTENCY_FLOOR,
    ICD_RECENCY_LAMBDA,
    ICD_WEIGHTS,
    ICD_WINDOW_DAYS,
    PROVENANCE_WEIGHTS,
    RISK_MAX,
    RISK_MIN,
)
from packages.shared import DailyLog

QualityMetrics = dict[str, float]


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _has_value(value: object) -> bool:
    if value is None or value is pd.NA:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    return not (isinstance(value, (list, tuple, set, dict)) and not value)


def _records(
    history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame,
) -> list[dict[str, Any]]:
    source = history.to_dict("records") if isinstance(history, pd.DataFrame) else history
    records: list[dict[str, Any]] = []
    for item in source:
        record = item.model_dump(mode="python") if isinstance(item, DailyLog) else dict(item)
        record["date"] = _as_date(record["date"])
        records.append(record)
    return records


def _provenance_weight(record: Mapping[str, Any], variable: str) -> float:
    provenance = record.get("field_provenance") or {}
    provenance_value = provenance.get(variable)
    if hasattr(provenance_value, "value"):
        provenance_value = provenance_value.value
    if provenance_value is None:
        provenance_value = "observed" if _has_value(record.get(variable)) else "unknown"
    return PROVENANCE_WEIGHTS.get(str(provenance_value), PROVENANCE_WEIGHTS["unknown"])


def _compute_coverage(records: list[dict[str, Any]], target_date: date) -> float:
    window_start = target_date - timedelta(days=ICD_WINDOW_DAYS - 1)
    window = [record for record in records if window_start <= record["date"] <= target_date]
    weighted_presence = 0.0
    total_importance = sum(ICD_WEIGHTS.values())
    for variable, importance in ICD_WEIGHTS.items():
        daily_weights: dict[date, float] = defaultdict(float)
        for record in window:
            daily_weights[record["date"]] = max(
                daily_weights[record["date"]],
                _provenance_weight(record, variable),
            )
        presence = sum(daily_weights.values()) / ICD_WINDOW_DAYS
        weighted_presence += importance * presence
    return float(np.clip(weighted_presence / total_importance, RISK_MIN, RISK_MAX))


def _is_recent_record(record: Mapping[str, Any]) -> bool:
    return any(
        _has_value(record.get(variable))
        for variable in ("sleep_hours", "sleep_quality", "night_awakenings", "crisis_occurred")
    )


def _compute_recency(records: list[dict[str, Any]], target_date: date) -> float:
    eligible_dates = [
        record["date"]
        for record in records
        if record["date"] <= target_date and _is_recent_record(record)
    ]
    if not eligible_dates:
        return RISK_MIN
    days_since_last_record = (target_date - max(eligible_dates)).days
    return math.exp(-ICD_RECENCY_LAMBDA * days_since_last_record)


def _normalized_disagreements(day_records: list[dict[str, Any]]) -> list[float]:
    disagreements: list[float] = []
    for variable in ICD_WEIGHTS:
        present = [record[variable] for record in day_records if _has_value(record.get(variable))]
        if len(present) < 2:
            continue
        if variable in CATEGORICAL_FIELDS:
            # A nominal answer has no distance: two sources either agree or they
            # do not, and a normalized gap would be meaningless.
            disagreements.extend(float(left != right) for left, right in combinations(present, 2))
            continue
        lower, upper = FIELD_RANGES[variable]
        legal_range = upper - lower
        values = [float(value) for value in present]
        disagreements.extend(
            abs(left - right) / legal_range for left, right in combinations(values, 2)
        )
    return disagreements


def _compute_consistency(records: list[dict[str, Any]], target_date: date) -> float:
    window_start = target_date - timedelta(days=ICD_WINDOW_DAYS - 1)
    records_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if window_start <= record["date"] <= target_date:
            records_by_day[record["date"]].append(record)

    daily_consistency: list[float] = []
    for day_records in records_by_day.values():
        if len({record.get("source") for record in day_records}) < 2:
            daily_consistency.append(RISK_MAX)
            continue
        disagreements = _normalized_disagreements(day_records)
        if not disagreements:
            daily_consistency.append(RISK_MAX)
            continue
        daily_consistency.append(
            float(
                np.clip(
                    RISK_MAX - float(np.mean(disagreements)),
                    ICD_CONSISTENCY_FLOOR,
                    RISK_MAX,
                )
            )
        )
    return float(np.mean(daily_consistency)) if daily_consistency else RISK_MAX


def compute_icd(
    history: Iterable[DailyLog | Mapping[str, Any]] | pd.DataFrame,
    target_date: date | datetime | str,
) -> QualityMetrics:
    """Compute coverage, recency, consistency, and their multiplicative ICD."""
    effective_date = _as_date(target_date)
    records = _records(history)
    coverage = _compute_coverage(records, effective_date)
    recency = _compute_recency(records, effective_date)
    consistency = _compute_consistency(records, effective_date)
    icd = float(np.clip(coverage * recency * consistency, RISK_MIN, RISK_MAX))
    return {
        "icd": icd,
        "coverage": coverage,
        "recency": recency,
        "consistency": consistency,
    }
