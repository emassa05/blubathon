"""Value of Information: which unanswered question would move today's estimate.

SPEC 7.1 defines it as expected variance reduction. For each missing variable
we sample plausible answers, re-score the day with each one, and take the
variance of the resulting risks. A variable that cannot move the number scores
zero; one that swings it scores high.

The imputation lives only here. The risk model itself never sees an imputed
value (SPEC rule 0.5) -- it receives NaN and handles it natively.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np

from ml.engine.pipeline import OverrideScorer, merge_today_values
from ml.features.personal import personal_stats
from ml.spec_constants import (
    BOOLEAN_FIELDS,
    CATEGORICAL_FIELDS,
    ORDINAL_MAX,
    ORDINAL_MIN,
    VOI_MIN_OBSERVATIONS,
    VOI_SAMPLES,
    VOI_SUGGESTION_WINDOW_DAYS,
)
from ml.voi.sampling import PopulationPrior, encode_answer, sample_values
from packages.shared import (
    MEDICATION_ADHERENCE_ANCHORS_ES,
    ORDINAL_ANCHORS_ES,
    VARIABLE_PROMPTS_ES,
)

# SPEC 12.4 gives a prompt for exactly the variables a person can be asked.
CANDIDATE_VARIABLES: tuple[str, ...] = tuple(VARIABLE_PROMPTS_ES)


def known_answers(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
) -> dict[str, Any]:
    """Everything already answered for one day, across every source."""
    return merge_today_values(history, target_date, CANDIDATE_VARIABLES)


def missing_variables(known: Mapping[str, Any]) -> list[str]:
    return [variable for variable in CANDIDATE_VARIABLES if known.get(variable) is None]


def _encoded(known: Mapping[str, Any]) -> dict[str, float | None]:
    return {variable: encode_answer(variable, value) for variable, value in known.items()}


def voi_for_variable(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    target_date: date | datetime | str,
    known: Mapping[str, Any],
    scorer: OverrideScorer,
    prior: PopulationPrior,
    k: int = VOI_SAMPLES,
) -> float:
    """SPEC 7.1: the variance of the risk across ``k`` imputations of ``variable``."""
    samples = sample_values(history, variable, target_date, prior, k=k)
    base = _encoded(known)
    override_sets = [{**base, variable: encode_answer(variable, sample)} for sample in samples]
    probabilities = scorer(override_sets)
    if len(probabilities) < 2:
        return 0.0
    return float(np.var(probabilities))


def suggestion_for(
    history: Iterable[Mapping[str, Any]],
    variable: str,
    target_date: date | datetime | str,
) -> tuple[Any, str | None]:
    """SPEC 7.6: the personal median over 14 days, only with enough observations.

    A suggestion is help, never an answer. It is rendered in grey next to an
    empty field and only becomes data when a person touches it (SPEC rule 0.12).
    """
    stats = personal_stats(
        history,
        variable,
        target_date,
        window_days=VOI_SUGGESTION_WINDOW_DAYS,
        min_observations=VOI_MIN_OBSERVATIONS,
    )
    if not stats["sufficient"]:
        return None, None
    median = float(stats["median"])
    if variable in CATEGORICAL_FIELDS:
        return None, None
    if variable in BOOLEAN_FIELDS:
        usual = median >= 0.5
        return usual, "lo habitual: sí" if usual else "lo habitual: no"
    if variable in ORDINAL_ANCHORS_ES:
        level = min(max(round(median), ORDINAL_MIN), ORDINAL_MAX)
        return level, ORDINAL_ANCHORS_ES[variable].get(level)
    if median.is_integer():
        return int(median), None
    return round(median, 2), None


def suggestion_label(variable: str, value: Any) -> str | None:
    """The frozen Spanish anchor for a value, when the scale has one (SPEC 12.5)."""
    if variable in CATEGORICAL_FIELDS:
        return MEDICATION_ADHERENCE_ANCHORS_ES.get(str(value))
    anchors = ORDINAL_ANCHORS_ES.get(variable)
    if anchors is None or not isinstance(value, int):
        return None
    return anchors.get(value)


def compute_voi(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    scorer: OverrideScorer,
    prior: PopulationPrior,
    known: Mapping[str, Any] | None = None,
    k: int = VOI_SAMPLES,
) -> list[dict[str, Any]]:
    """Rank every unanswered variable for one day, highest value first.

    Passing ``known`` drives the sequential recomputation of SPEC 7.3: the
    second question is chosen with the first one already answered.
    """
    records = list(history)
    answered = dict(known) if known is not None else known_answers(records, target_date)
    ranked = []
    for variable in missing_variables(answered):
        suggestion, label = suggestion_for(records, variable, target_date)
        ranked.append(
            {
                "variable": variable,
                "voi": voi_for_variable(
                    records, variable, target_date, answered, scorer, prior, k=k
                ),
                "suggestion": suggestion,
                "suggestion_label_es": label,
            }
        )
    ranked.sort(key=lambda entry: (-entry["voi"], entry["variable"]))
    return ranked


def sequential_recompute(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    scorer: OverrideScorer,
    prior: PopulationPrior,
    answers: Sequence[tuple[str, Any]],
) -> list[list[dict[str, Any]]]:
    """SPEC 7.3: the ranking after each answer, in the order they were given."""
    records = list(history)
    known = known_answers(records, target_date)
    rankings = [compute_voi(records, target_date, scorer, prior, known=known)]
    for variable, value in answers:
        known = {**known, variable: value}
        rankings.append(compute_voi(records, target_date, scorer, prior, known=known))
    return rankings
