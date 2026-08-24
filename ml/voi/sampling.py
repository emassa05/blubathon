"""Muestreo con degradación por antigüedad — SPEC §7.2.

`POPULATION_PRIOR*` son el prior poblacional de cold-start (§8.4). El SPEC
exige que salga de "el conjunto de train" del generador sintético (§8), que
es responsabilidad de P1 (`ml/synth/`, ~5h, fuera del alcance de P2). Mientras
ese generador no exista, se usa aquí una aproximación razonable, coherente
con las direcciones y rangos de §2.1 y con los targets de §8.5. Reemplazar
por el prior real calculado sobre train en cuanto `ml/synth` esté disponible
(no requiere tocar ninguna otra función de este módulo).
"""

from __future__ import annotations

import numpy as np

from ml.features.personal import days_since_observed, history_days_count, personal_stats
from ml.spec_constants import (
    FIELD_RANGES,
    ORDINAL_1_5_FIELDS,
    RANDOM_SEED,
    VOI_K,
    VOI_KAPPA,
    VOI_PRIOR_MIN_HISTORY_DAYS,
    VOI_PRIOR_MIN_OBSERVATIONS,
)
from ml.voi.util import stable_hash_int

POPULATION_PRIOR: dict[str, tuple[float, float]] = {
    "sleep_hours": (8.5, 1.0),
    "sleep_quality": (4.0, 1.0),
    "night_awakenings": (1.0, 1.0),
    "wake_state": (4.0, 1.0),
    "morning_support_need": (2.0, 1.0),
    "gi_status": (4.0, 1.0),
    "alertness": (3.0, 1.0),
    "dysregulation_events": (1.0, 1.0),
    "activity_participation": (4.0, 1.0),
    "social_interactions": (4.0, 1.0),
    "eating_status": (4.0, 1.0),
}

POPULATION_PRIOR_BOOL: dict[str, float] = {
    "food_changes": 0.125,
    "routine_changes": 0.125,
    "relevant_event_flag": 0.125,
}

BOOL_CANDIDATE_FIELDS = frozenset(POPULATION_PRIOR_BOOL)


def _rng_for(date: str, variable: str) -> np.random.Generator:
    seed = stable_hash_int(f"{RANDOM_SEED}|{date}|{variable}") % (2**32)
    return np.random.default_rng(seed)


def _round_and_clip(values: np.ndarray, variable: str) -> list:
    lo, hi = FIELD_RANGES.get(variable, (-np.inf, np.inf))
    clipped = np.clip(values, lo, hi)
    if variable in ORDINAL_1_5_FIELDS or variable == "night_awakenings" or variable == "dysregulation_events":
        return [int(round(v)) for v in clipped]
    return [float(v) for v in clipped]


def uses_prior(history: list[dict], variable: str, date: str) -> bool:
    if history_days_count(history, date) < VOI_PRIOR_MIN_HISTORY_DAYS:
        return True
    stats = personal_stats(history, variable, date, min_observations=VOI_PRIOR_MIN_OBSERVATIONS)
    return not stats["sufficient"]


def sample_values(history: list[dict], variable: str, date: str, k: int = VOI_K) -> list:
    """SPEC §7.1–§7.2. `K` muestras plausibles de `variable` en `date`."""
    rng = _rng_for(date, variable)

    if variable in BOOL_CANDIDATE_FIELDS:
        if uses_prior(history, variable, date):
            p_true = POPULATION_PRIOR_BOOL[variable]
        else:
            window = [
                bool(log[variable])
                for log in history
                if log["date"] <= date
                and log.get(variable) is not None
                and (log.get("field_provenance") or {}).get(variable, "observed") in ("observed", "confirmed")
            ][-30:]
            p_true = (sum(window) / len(window)) if window else POPULATION_PRIOR_BOOL[variable]
        return [bool(x) for x in (rng.random(k) < p_true)]

    if uses_prior(history, variable, date):
        median, mad = POPULATION_PRIOR[variable]
        d_v = days_since_observed(history, variable, date) or 0
    else:
        stats = personal_stats(history, variable, date)
        median, mad = stats["median"], stats["mad"]
        if mad == 0:
            mad = POPULATION_PRIOR[variable][1] * 0.25  # evita varianza degenerada
        d_v = days_since_observed(history, variable, date) or 0

    sigma = mad * (1 + VOI_KAPPA * d_v)
    if sigma <= 0:
        raw = np.full(k, median)
    else:
        raw = rng.normal(median, sigma, size=k)
    return _round_and_clip(raw, variable)
