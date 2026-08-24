"""The adaptive form and the three safeguards against the blind spot (SPEC 7.4-7.5).

Pure Value of Information is pure exploitation: it could stop asking about a
stable variable and never learn that it changed. Three safeguards prevent that,
and the filter question never overrides them. The form orders and highlights;
it never hides (SPEC rule 0.13) -- every variable stays reachable in block 4.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

from ml.engine.pipeline import OverrideScorer
from ml.features.personal import days_since_observed, personal_stats, robust_z_score
from ml.spec_constants import (
    HIGH_WEIGHT_FIELDS,
    ICD_WEIGHTS,
    ICD_WINDOW_DAYS,
    PREDICTION_HORIZON_DAYS,
    VOI_ANOMALY_THRESHOLD,
    VOI_DEFAULT_HIGHLIGHTED,
    VOI_EXPLORATION_MODULO,
    VOI_LOW_ICD_HIGHLIGHTED,
    VOI_LOW_ICD_THRESHOLD,
    VOI_SAMPLES,
    VOI_STALENESS_CEILING_DAYS,
)
from ml.voi.compute import compute_voi, known_answers
from ml.voi.sampling import PopulationPrior, staleness_days
from ml.voi.util import stable_hash_int
from packages.shared import CLOSING_QUESTION_TEMPLATE_ES, FILTER_QUESTION_ES, VARIABLE_PROMPTS_ES

Reason = str


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def highlighted_size(icd: float) -> int:
    """Two questions, or three when data quality is poor enough to need them."""
    return VOI_LOW_ICD_HIGHLIGHTED if icd < VOI_LOW_ICD_THRESHOLD else VOI_DEFAULT_HIGHLIGHTED


def staleness_candidates(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    missing: Iterable[str],
) -> list[str]:
    """SPEC 7.5a: no high-weight variable may go unasked for more than 7 days.

    Ties break by importance, then by how long it has been, then alphabetically,
    so two variables reaching the ceiling on the same day resolve identically on
    every run.
    """
    missing_set = set(missing)
    candidates = [
        variable
        for variable in HIGH_WEIGHT_FIELDS
        if variable in missing_set
        and staleness_days(history, variable, target_date) >= VOI_STALENESS_CEILING_DAYS
    ]
    candidates.sort(
        key=lambda variable: (
            -ICD_WEIGHTS[variable],
            -staleness_days(history, variable, target_date),
            variable,
        )
    )
    return candidates


def exploration_triggered(child_id: str, target_date: date | datetime | str) -> bool:
    """SPEC 7.5c: a deterministic one-day-in-seven exploration slot."""
    return stable_hash_int(f"{child_id}{target_date}") % VOI_EXPLORATION_MODULO == 0


def least_observed_high_weight(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    missing: Iterable[str],
) -> str | None:
    """The high-weight variable seen least often in the recent window."""
    pool = sorted(set(missing) & set(HIGH_WEIGHT_FIELDS))
    if not pool:
        return None
    records = list(history)
    counts = {
        variable: personal_stats(records, variable, target_date, window_days=ICD_WINDOW_DAYS)[
            "n_observations"
        ]
        for variable in pool
    }
    fewest = min(counts.values())
    return next(variable for variable in pool if counts[variable] == fewest)


def detect_anomaly(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    known: Mapping[str, Any],
) -> bool:
    """SPEC 7.5b: any answer two robust deviations from personal normal opens the tail."""
    records = list(history)
    for variable, value in known.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        stats = personal_stats(records, variable, target_date)
        if not stats["sufficient"]:
            continue
        z = robust_z_score(float(value), stats["median"], stats["mad"])
        if not math.isnan(z) and abs(z) >= VOI_ANOMALY_THRESHOLD:
            return True
    return False


def closing_question(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
) -> tuple[str | None, date | None]:
    """Close the loop on yesterday's prediction if nobody reported the outcome.

    Without this the system never learns whether it was right: ``crisis_occurred``
    is the only label there is, and it is only knowable after the day ends.
    """
    previous = _as_date(target_date) - timedelta(days=PREDICTION_HORIZON_DAYS)
    reported = any(
        _as_date(log["date"]) == previous and log.get("crisis_occurred") is not None
        for log in history
    )
    if reported:
        return None, None
    return CLOSING_QUESTION_TEMPLATE_ES.format(target_date=previous.isoformat()), previous


def _item(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    ranked: Mapping[str, Any],
    reason: Reason,
) -> dict[str, Any]:
    variable = ranked["variable"]
    return {
        "variable": variable,
        "prompt_es": VARIABLE_PROMPTS_ES[variable],
        "voi": float(ranked["voi"]),
        "reason": reason,
        "suggestion": ranked["suggestion"],
        "suggestion_label_es": ranked["suggestion_label_es"],
        "days_since_observed": days_since_observed(history, variable, target_date),
    }


def _replace_weakest(
    highlighted: list[str],
    reasons: dict[str, Reason],
    ranked_by_variable: Mapping[str, Mapping[str, Any]],
    incoming: str,
    reason: Reason,
) -> None:
    """Displace the lowest-value slot. The block keeps its size (SPEC 7.5a)."""
    weakest = min(highlighted, key=lambda variable: ranked_by_variable[variable]["voi"])
    highlighted[highlighted.index(weakest)] = incoming
    reasons.pop(weakest, None)
    reasons[incoming] = reason


def build_form(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    child_id: str,
    icd: float,
    scorer: OverrideScorer,
    prior: PopulationPrior,
    known: Mapping[str, Any] | None = None,
    k: int = VOI_SAMPLES,
) -> dict[str, Any]:
    """Assemble the four blocks of SPEC 7.4 with the safeguards of SPEC 7.5."""
    records = list(history)
    answered = dict(known) if known is not None else known_answers(records, target_date)
    ranked = compute_voi(records, target_date, scorer, prior, known=answered, k=k)
    ranked_by_variable = {entry["variable"]: entry for entry in ranked}

    size = highlighted_size(icd)
    highlighted = [entry["variable"] for entry in ranked[:size]]
    reasons: dict[str, Reason] = dict.fromkeys(highlighted, "voi")

    stale = staleness_candidates(records, target_date, ranked_by_variable)
    for variable in stale:
        if variable in highlighted:
            # Already surfaced by value, but staleness is the more useful thing
            # to tell a person: "this has not been recorded in seven days".
            reasons[variable] = "staleness"
            continue
        if not highlighted:
            break
        _replace_weakest(highlighted, reasons, ranked_by_variable, variable, "staleness")

    # SPEC 7.5: the staleness ceiling outranks the exploration quota.
    if not stale and exploration_triggered(child_id, target_date) and highlighted:
        candidate = least_observed_high_weight(records, target_date, ranked_by_variable)
        if candidate is not None and candidate not in highlighted:
            _replace_weakest(highlighted, reasons, ranked_by_variable, candidate, "exploration")

    closing_question_es, closing_target_date = closing_question(records, target_date)
    return {
        "child_id": child_id,
        "date": _as_date(target_date),
        "highlighted": [
            _item(records, target_date, ranked_by_variable[variable], reasons[variable])
            for variable in highlighted
        ],
        "filter_question_es": FILTER_QUESTION_ES,
        "tail": [
            _item(records, target_date, entry, "voi")
            for entry in ranked
            if entry["variable"] not in highlighted
        ],
        "closing_question_es": closing_question_es,
        "closing_target_date": closing_target_date,
    }


def resolve_filter_answer(
    history: Iterable[Mapping[str, Any]],
    target_date: date | datetime | str,
    tail_variables: Sequence[str],
    known: Mapping[str, Any],
    *,
    nothing_unusual: bool,
) -> dict[str, str]:
    """Turn the filter answer into provenance for the tail (SPEC 7.4, 2.5).

    Answering "no" is information, not silence: the tail becomes
    ``assumed_stable`` and never receives a value. An anomaly in what was
    already answered opens the tail anyway (SPEC 7.5b).
    """
    if not nothing_unusual:
        return {}
    if detect_anomaly(history, target_date, known):
        return {}
    return dict.fromkeys(tail_variables, "assumed_stable")
