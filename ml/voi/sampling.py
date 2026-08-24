"""Plausible answers for a missing variable, widened by staleness (SPEC 7.2).

Certainty about an unobserved variable decays with time. Sampling from the
child's own distribution, widened by how long ago the variable was last seen,
makes a long-unasked variable score high on its own: the samples spread, the
predictions spread, and the Value of Information rises without any ad-hoc rule.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

import numpy as np

from ml.errors import ContractViolationError
from ml.features.personal import days_since_observed, history_days_count, personal_stats
from ml.spec_constants import (
    BOOLEAN_FIELDS,
    CATEGORICAL_FIELDS,
    FIELD_RANGES,
    MEDICATION_ADHERENCE_CODES,
    NIGHT_AWAKENINGS_MAX,
    ORDINAL_FIELDS,
    RANDOM_SEED,
    VOI_KAPPA,
    VOI_MIN_OBSERVATIONS,
    VOI_PERSONAL_HISTORY_DAYS,
    VOI_PERSONAL_WINDOW_DAYS,
    VOI_SAMPLES,
    VOI_STALENESS_CEILING_DAYS,
)
from ml.voi.util import stable_hash_int

PopulationPrior = Mapping[str, Mapping[str, float]]

_INTEGER_FIELDS = frozenset(ORDINAL_FIELDS) | {"night_awakenings", "dysregulation_events"}
_BOOLEAN_CANDIDATES = frozenset(BOOLEAN_FIELDS) - {"crisis_occurred"}
_MEDICATION_CODES = tuple(sorted(MEDICATION_ADHERENCE_CODES.values()))
# Without any history at all, a variable still needs a spread wide enough for
# the model to react. One unit on a 1-5 scale is the smallest visible step.
_FALLBACK_MAD = 1.0


def _rng_for(target_date: date | datetime | str, variable: str) -> np.random.Generator:
    """SPEC rule 0.9: the same child-day-variable always draws the same samples."""
    key = f"{RANDOM_SEED}|{target_date}|{variable}"
    return np.random.default_rng(stable_hash_int(key) % (2**32))


def _quantise(values: np.ndarray, variable: str) -> list[Any]:
    low, high = FIELD_RANGES.get(variable, (-np.inf, np.inf))
    clipped = np.clip(values, low, high)
    if variable in _INTEGER_FIELDS:
        return [round(float(value)) for value in clipped]
    return [float(value) for value in clipped]


def _prior_for(prior: PopulationPrior, variable: str) -> tuple[float, float]:
    entry = prior.get(variable)
    if entry is None:
        low, high = FIELD_RANGES.get(variable, (0.0, 1.0))
        return (low + high) / 2, _FALLBACK_MAD
    mad = float(entry.get("mad") or 0.0)
    return float(entry["median"]), mad if mad > 0 else _FALLBACK_MAD


def uses_population_prior(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    target_date: date | datetime | str,
) -> bool:
    """SPEC 7.2: too little history of their own means fall back to the cohort."""
    records = list(history)
    if history_days_count(records, target_date) < VOI_PERSONAL_HISTORY_DAYS:
        return True
    stats = personal_stats(
        records,
        variable,
        target_date,
        window_days=VOI_PERSONAL_WINDOW_DAYS,
        min_observations=VOI_MIN_OBSERVATIONS,
    )
    return not stats["sufficient"]


def staleness_days(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    target_date: date | datetime | str,
) -> int:
    """``d_v``, treating never-observed as one day past the staleness ceiling."""
    observed = days_since_observed(history, variable, target_date)
    return VOI_STALENESS_CEILING_DAYS + 1 if observed is None else observed


def sample_values(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    target_date: date | datetime | str,
    prior: PopulationPrior,
    k: int = VOI_SAMPLES,
) -> list[Any]:
    """Draw ``k`` plausible values for one missing variable on one day.

    Spread is ``MAD * (1 + kappa * d_v)``: at seven days without an observation
    the dispersion has roughly doubled (SPEC 7.2).
    """
    if k < 1:
        raise ContractViolationError("value-of-information needs at least one sample")
    records = list(history)
    rng = _rng_for(target_date, variable)
    d_v = staleness_days(records, variable, target_date)
    use_prior = uses_population_prior(records, variable, target_date)

    if variable in _BOOLEAN_CANDIDATES:
        entry = prior.get(variable)
        rate = float(entry["mean"]) if entry and "mean" in entry else 0.5
        if not use_prior:
            stats = personal_stats(
                records, variable, target_date, window_days=VOI_PERSONAL_WINDOW_DAYS
            )
            if stats["n_observations"]:
                rate = float(stats["median"])
        # A stale flag drifts back towards "could be either" instead of staying
        # pinned at whatever it was the last time anyone looked.
        drift = min(1.0, VOI_KAPPA * d_v)
        rate = rate * (1 - drift) + 0.5 * drift
        return [bool(value) for value in rng.random(k) < rate]

    if variable in CATEGORICAL_FIELDS:
        return [int(value) for value in rng.choice(np.asarray(_MEDICATION_CODES), size=k)]

    if use_prior:
        median, mad = _prior_for(prior, variable)
    else:
        stats = personal_stats(records, variable, target_date, window_days=VOI_PERSONAL_WINDOW_DAYS)
        median = float(stats["median"])
        mad = float(stats["mad"])
        if mad <= 0:
            # A perfectly stable variable still deserves a testable spread.
            mad = _prior_for(prior, variable)[1] / 4
    sigma = mad * (1 + VOI_KAPPA * d_v)
    if sigma <= 0:
        return _quantise(np.full(k, median), variable)
    return _quantise(rng.normal(median, sigma, size=k), variable)


def encode_answer(variable: str, value: Any) -> float | None:
    """Turn one contract-level answer into the number the model expects."""
    if value is None:
        return None
    if variable in CATEGORICAL_FIELDS:
        if isinstance(value, str):
            return float(MEDICATION_ADHERENCE_CODES[value])
        return float(value)
    if isinstance(value, bool):
        return float(value)
    if variable == "night_awakenings":
        return float(min(int(value), NIGHT_AWAKENINGS_MAX))
    return float(value)
