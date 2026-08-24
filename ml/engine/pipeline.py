"""Assemble quality, features, model and decision into one prediction (SPEC 9, 6).

This is the only place that knows the order of the four layers. It stays pure:
it receives a fitted ensemble and a child's history, and returns values. Reading
the database and serialising HTTP belong to ``apps/api`` (CONVENTIONS 2).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from ml.engine.decision import AbstentionReason, abstention_reasons, confidence_label, risk_band
from ml.engine.model import RiskEnsemble
from ml.features.baseline import PointInTimeFeatures
from ml.features.personal import history_days_count
from ml.features.quality import compute_icd
from ml.spec_constants import PREDICTION_HORIZON_DAYS, RISK_API_DECIMALS

OverrideScorer = Callable[[Sequence[Mapping[str, Any]]], np.ndarray]


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass(frozen=True)
class RiskAssessment:
    """One child-day: the number, its uncertainty, and why it may be withheld."""

    child_id: str
    as_of_date: date
    target_date: date
    probability: float
    interval: tuple[float, float]
    standard_deviation: float
    quality: dict[str, float]
    history_days: int
    reasons: tuple[AbstentionReason, ...]

    @property
    def width(self) -> float:
        return self.interval[1] - self.interval[0]

    @property
    def abstains(self) -> bool:
        return bool(self.reasons)

    @property
    def band(self) -> str | None:
        return None if self.abstains else risk_band(self.probability)

    @property
    def confidence(self) -> str | None:
        return None if self.abstains else confidence_label(self.quality["icd"], self.width)


def target_date_for(as_of_date: date | datetime | str) -> date:
    """SPEC 3: the horizon is exactly one calendar day."""
    return _as_date(as_of_date) + timedelta(days=PREDICTION_HORIZON_DAYS)


def merge_today_values(
    history: Iterable[Mapping[str, Any]],
    as_of_date: date | datetime | str,
    fields: Iterable[str],
) -> dict[str, Any]:
    """Combine every source that reported on one day into a single answer set.

    SPEC 2.3 lets home, therapy and school each report part of the same day; the
    first source that actually answered a field wins, and a field nobody
    answered stays absent rather than becoming a zero (SPEC rule 0.6).
    """
    target = _as_date(as_of_date)
    known: dict[str, Any] = {}
    for log in history:
        if _as_date(log["date"]) != target:
            continue
        for field in fields:
            if log.get(field) is not None and known.get(field) is None:
                known[field] = log[field]
    return known


def make_override_scorer(
    ensemble: RiskEnsemble,
    context: PointInTimeFeatures,
) -> OverrideScorer:
    """Return a batched scorer: many hypothetical answer sets, one model call."""

    def score(override_sets: Sequence[Mapping[str, Any]]) -> np.ndarray:
        if not override_sets:
            return np.empty(0)
        rows = [context.row_with(overrides) for overrides in override_sets]
        frame = pd.concat(rows, ignore_index=True)
        return ensemble.predict(frame).probability

    return score


def assess_risk(
    ensemble: RiskEnsemble,
    history: Iterable[Mapping[str, Any]],
    child_id: str,
    as_of_date: date | datetime | str,
    *,
    context: PointInTimeFeatures | None = None,
) -> RiskAssessment:
    """Score ``as_of_date + 1`` using only records up to and including that day.

    The anti-leakage rule (SPEC rule 0.2) is enforced by the caller passing a
    history already truncated at ``as_of_date``; nothing here reads later rows.
    """
    records = list(history)
    as_of = _as_date(as_of_date)
    prepared = context or PointInTimeFeatures(records, child_id, as_of)
    prediction = ensemble.predict(prepared.base_row())
    probability = float(prediction.probability[0])
    interval = (float(prediction.lower[0]), float(prediction.upper[0]))
    quality = compute_icd(records, as_of)
    history_days = history_days_count(records, as_of)
    return RiskAssessment(
        child_id=str(child_id),
        as_of_date=as_of,
        target_date=target_date_for(as_of),
        probability=probability,
        interval=interval,
        standard_deviation=float(prediction.standard_deviation[0]),
        quality=quality,
        history_days=history_days,
        reasons=abstention_reasons(quality["icd"], interval[1] - interval[0], history_days),
    )


def counterfactual_probabilities(
    ensemble: RiskEnsemble,
    history: Iterable[Mapping[str, Any]],
    child_id: str,
    as_of_date: date | datetime | str,
    overrides: Mapping[str, Any],
) -> tuple[float, float]:
    """Score the same day before and after replacing some of today's answers.

    Strictly literal: only the named fields move, and everything else stays as
    recorded. Fields that are strongly correlated in the data therefore share
    their explanatory power, so a single-variable slider on one of them reads
    weaker than the driver list suggests.
    """
    context = PointInTimeFeatures(history, child_id, _as_date(as_of_date))
    score = make_override_scorer(ensemble, context)
    before, after = score([{}, dict(overrides)])
    return round(float(before), RISK_API_DECIMALS), round(float(after), RISK_API_DECIMALS)
