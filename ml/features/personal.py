"""Record-oriented personal baselines used by the elicitation layer (SPEC 9.1).

``baseline.py`` builds the model's feature matrix with pandas over a whole
cohort. The Value-of-Information loop (SPEC 7.1) needs the same personal
median/MAD for a single child, one variable at a time, hundreds of times per
request. These helpers answer that question directly over the log dictionaries,
with the same window and provenance rules as the matrix builder.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import Any

from ml.spec_constants import (
    FEATURE_MAD_SCALE,
    FEATURE_MIN_OBSERVATIONS,
    FEATURE_ROBUST_WINDOW_MAX_DAYS,
    FEATURE_ZERO_MAD_SCALE,
    PROVENANCE_WEIGHTS,
)

# SPEC 2.5: only a value a person actually entered or confirmed counts as an
# observation. assumed_stable contributes coverage but never a value.
_VALUED_PROVENANCE = frozenset(
    provenance for provenance, weight in PROVENANCE_WEIGHTS.items() if weight >= 1.0
)

PersonalStats = dict[str, Any]


def _as_date(value: date_cls | datetime | str) -> date_cls:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_cls):
        return value
    return date_cls.fromisoformat(value)


def _is_observed(log: Mapping[str, Any], variable: str) -> bool:
    if log.get(variable) is None:
        return False
    provenance = (log.get("field_provenance") or {}).get(variable, "observed")
    return provenance in _VALUED_PROVENANCE


def _observed_values(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    as_of: date_cls,
    window_days: int,
) -> list[float]:
    window_start = as_of - timedelta(days=window_days - 1)
    values = []
    for log in history:
        day = _as_date(log["date"])
        if window_start <= day <= as_of and _is_observed(log, variable):
            values.append(float(log[variable]))
    return values


def _median(sorted_values: list[float]) -> float:
    count = len(sorted_values)
    middle = count // 2
    if count % 2:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2


def robust_stats(values: list[float]) -> tuple[float, float]:
    """Return the median and median absolute deviation, or NaN when empty."""
    if not values:
        return math.nan, math.nan
    median = _median(sorted(values))
    return median, _median(sorted(abs(value - median) for value in values))


def personal_stats(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    as_of_date: date_cls | datetime | str,
    window_days: int = FEATURE_ROBUST_WINDOW_MAX_DAYS,
    min_observations: int = FEATURE_MIN_OBSERVATIONS,
) -> PersonalStats:
    """Summarise one child's own distribution for one variable up to a date."""
    values = _observed_values(history, variable, _as_date(as_of_date), window_days)
    median, mad = robust_stats(values)
    return {
        "median": median,
        "mad": mad,
        "n_observations": len(values),
        "sufficient": len(values) >= min_observations,
    }


def robust_z_score(value: float, median: float, mad: float) -> float:
    """Scale a deviation by the personal MAD, returning NaN without a baseline.

    Never returns 0 for "no information" (SPEC rule 0.6): an absent baseline is
    NaN, and only a value that truly sits on the median scores zero.
    """
    if math.isnan(median) or math.isnan(mad):
        return math.nan
    scale = mad * FEATURE_MAD_SCALE
    if scale <= 0.0:
        # A perfectly flat history would otherwise make every deviation
        # infinite. The matrix builder floors the scale the same way, so both
        # paths agree on what counts as unusual.
        scale = FEATURE_ZERO_MAD_SCALE
    return (value - median) / scale


def days_since_observed(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    as_of_date: date_cls | datetime | str,
) -> int | None:
    """Return ``d_v`` from SPEC 7.2, or None when the variable was never seen."""
    as_of = _as_date(as_of_date)
    latest: date_cls | None = None
    for log in history:
        day = _as_date(log["date"])
        if day > as_of or not _is_observed(log, variable):
            continue
        if latest is None or day > latest:
            latest = day
    return None if latest is None else (as_of - latest).days


def history_days_count(
    history: Iterable[Mapping[str, Any]],
    as_of_date: date_cls | datetime | str,
) -> int:
    """Count distinct days with at least one record, up to and including a date."""
    as_of = _as_date(as_of_date)
    return len({log["date"] for log in history if _as_date(log["date"]) <= as_of})
