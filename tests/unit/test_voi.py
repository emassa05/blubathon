"""Value of Information and the adaptive form (SPEC 7)."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import pytest

from ml.spec_constants import (
    FIELD_RANGES,
    HIGH_WEIGHT_FIELDS,
    ICD_WEIGHTS,
    ORDINAL_FIELDS,
    VOI_DEFAULT_HIGHLIGHTED,
    VOI_LOW_ICD_HIGHLIGHTED,
    VOI_SAMPLES,
    VOI_STALENESS_CEILING_DAYS,
)
from ml.voi import (
    build_form,
    compute_voi,
    detect_anomaly,
    exploration_triggered,
    highlighted_size,
    known_answers,
    missing_variables,
    resolve_filter_answer,
    sample_values,
    sequential_recompute,
    staleness_candidates,
    suggestion_for,
)
from tests.conftest import last_date

pytestmark = pytest.mark.filterwarnings("ignore")


def _history_without(history, variables, on_date):
    """Drop some of today's answers so those variables count as missing."""
    stripped = []
    for log in history:
        copy = dict(log)
        if copy["date"] == on_date.isoformat():
            for variable in variables:
                copy[variable] = None
                copy["field_provenance"] = {
                    key: value
                    for key, value in (copy.get("field_provenance") or {}).items()
                    if key != variable
                }
        stripped.append(copy)
    return stripped


def test_k_is_twenty_and_reproducible(calm_history, population_prior):
    """SPEC 7.1: twenty samples, and seed 42 makes them repeatable."""
    as_of = last_date(calm_history)
    first = sample_values(calm_history, "gi_status", as_of, population_prior)
    second = sample_values(calm_history, "gi_status", as_of, population_prior)
    assert len(first) == VOI_SAMPLES
    assert first == second


def test_samples_are_clipped_and_typed(calm_history, population_prior):
    """SPEC 7.2: samples respect the legal range and the declared type."""
    as_of = last_date(calm_history)
    for variable in ("sleep_quality", "gi_status", "night_awakenings", "sleep_hours"):
        low, high = FIELD_RANGES[variable]
        for value in sample_values(calm_history, variable, as_of, population_prior):
            assert low <= value <= high
            if variable in ORDINAL_FIELDS or variable == "night_awakenings":
                assert isinstance(value, int)


def test_staleness_widens_the_spread(calm_history, population_prior):
    """SPEC 7.2: a variable unseen for eight days spreads wider than a fresh one."""
    as_of = last_date(calm_history)
    fresh = sample_values(calm_history, "gi_status", as_of, population_prior)
    stale_history = _history_without(calm_history, ["gi_status"], as_of)
    for offset in range(1, 9):
        stale_history = _history_without(
            stale_history, ["gi_status"], as_of - timedelta(days=offset)
        )
    stale = sample_values(stale_history, "gi_status", as_of, population_prior)
    assert _spread(stale) >= _spread(fresh)


def _spread(values):
    numeric = [float(value) for value in values]
    mean = sum(numeric) / len(numeric)
    return sum((value - mean) ** 2 for value in numeric) / len(numeric)


def test_answered_variables_leave_the_ranking(calm_history, population_prior, scorer_factory):
    """SPEC 7.1: only missing variables are worth asking about."""
    as_of = last_date(calm_history)
    scorer, _ = scorer_factory(calm_history, as_of)
    ranked = compute_voi(calm_history, as_of, scorer, population_prior)
    answered = known_answers(calm_history, as_of)
    for entry in ranked:
        assert answered.get(entry["variable"]) is None


def test_ranking_is_sorted_and_non_negative(calm_history, population_prior, scorer_factory):
    """Variance is never negative, and the highest value comes first."""
    as_of = last_date(calm_history)
    scorer, _ = scorer_factory(calm_history, as_of)
    ranked = compute_voi(calm_history, as_of, scorer, population_prior)
    values = [entry["voi"] for entry in ranked]
    assert all(value >= 0 for value in values)
    assert values == sorted(values, reverse=True)


def test_sequential_recomputation_changes_the_next_question(
    calm_history, population_prior, scorer_factory
):
    """SPEC 7.3: the second question is chosen with the first already answered."""
    as_of = last_date(calm_history)
    stripped = _history_without(calm_history, ["gi_status", "sleep_hours"], as_of)
    scorer, _ = scorer_factory(stripped, as_of)
    rankings = sequential_recompute(stripped, as_of, scorer, population_prior, [("gi_status", 2)])
    assert len(rankings) == 2
    assert "gi_status" in {entry["variable"] for entry in rankings[0]}
    assert "gi_status" not in {entry["variable"] for entry in rankings[1]}


def test_suggestion_needs_five_observations(calm_history):
    """SPEC 7.6: below five observations in fourteen days there is no suggestion."""
    as_of = last_date(calm_history)
    thin = calm_history[:3]
    assert suggestion_for(thin, "sleep_quality", as_of) == (None, None)
    value, label = suggestion_for(calm_history, "sleep_quality", as_of)
    if value is not None:
        assert 1 <= value <= 5
        assert isinstance(label, str) and label


def test_highlighted_block_size(calm_history, population_prior, scorer_factory):
    """SPEC 7.4: two questions, three when ICD is below one half."""
    as_of = last_date(calm_history)
    child_id = calm_history[0]["child_id"]
    scorer, _ = scorer_factory(calm_history, as_of)
    missing = len(missing_variables(known_answers(calm_history, as_of)))
    good = build_form(calm_history, as_of, child_id, 0.8, scorer, population_prior)
    poor = build_form(calm_history, as_of, child_id, 0.4, scorer, population_prior)
    assert len(good["highlighted"]) == min(VOI_DEFAULT_HIGHLIGHTED, missing)
    assert len(poor["highlighted"]) == min(VOI_LOW_ICD_HIGHLIGHTED, missing)
    assert highlighted_size(0.8) == VOI_DEFAULT_HIGHLIGHTED
    assert highlighted_size(0.4) == VOI_LOW_ICD_HIGHLIGHTED


def test_form_carries_the_frozen_filter_question(calm_history, population_prior, scorer_factory):
    """SPEC 7.4: block 2 is one fixed question, not a paraphrase."""
    as_of = last_date(calm_history)
    scorer, _ = scorer_factory(calm_history, as_of)
    form = build_form(
        calm_history, as_of, calm_history[0]["child_id"], 0.8, scorer, population_prior
    )
    from packages.shared import FILTER_QUESTION_ES

    assert form["filter_question_es"] == FILTER_QUESTION_ES


def test_staleness_ceiling_displaces_without_growing_the_block(
    calm_history, population_prior, scorer_factory
):
    """SPEC 7.5a: a stale high-weight variable takes a slot, it does not add one."""
    as_of = last_date(calm_history)
    stale_history = calm_history
    for offset in range(0, VOI_STALENESS_CEILING_DAYS + 2):
        stale_history = _history_without(
            stale_history, ["gi_status"], as_of - timedelta(days=offset)
        )
    scorer, _ = scorer_factory(stale_history, as_of)
    form = build_form(
        stale_history, as_of, stale_history[0]["child_id"], 0.8, scorer, population_prior
    )
    assert len(form["highlighted"]) == VOI_DEFAULT_HIGHLIGHTED
    reasons = {item["variable"]: item["reason"] for item in form["highlighted"]}
    assert reasons.get("gi_status") == "staleness"


def test_staleness_tie_break_is_importance_then_age_then_name(calm_history):
    """SPEC 7.5a: two variables reaching the ceiling resolve the same way every run."""
    as_of = last_date(calm_history)
    empty_history = [{"date": (as_of - timedelta(days=20)).isoformat(), "child_id": "x"}]
    candidates = staleness_candidates(empty_history, as_of, HIGH_WEIGHT_FIELDS)
    weights = [ICD_WEIGHTS[variable] for variable in candidates]
    assert weights == sorted(weights, reverse=True)
    for first, second in pairwise(candidates):
        if ICD_WEIGHTS[first] == ICD_WEIGHTS[second]:
            assert first < second


def test_exploration_quota_is_deterministic():
    """SPEC 7.5c: the same child and day always give the same answer."""
    child_id = "10000000-0000-4000-8000-000000000000"
    day = date(2026, 8, 20)
    assert exploration_triggered(child_id, day) == exploration_triggered(child_id, day)
    fired = sum(
        exploration_triggered(child_id, date(2026, 1, 1) + timedelta(days=offset))
        for offset in range(70)
    )
    assert 3 <= fired <= 20, "roughly one day in seven"


def test_anomaly_trigger_opens_the_tail(calm_history):
    """SPEC 7.5b: an answer far from personal normal overrides a 'no' filter."""
    as_of = last_date(calm_history)
    normal = known_answers(calm_history, as_of)
    assert not detect_anomaly(calm_history, as_of, {"sleep_hours": normal.get("sleep_hours", 9.0)})
    assert detect_anomaly(calm_history, as_of, {"sleep_hours": 2.0})


def test_filter_no_assigns_assumed_stable_without_values(calm_history):
    """SPEC 7.4: answering 'nothing new' adds provenance, never a number."""
    as_of = last_date(calm_history)
    tail = ["gi_status", "eating_status"]
    provenance = resolve_filter_answer(
        calm_history, as_of, tail, {"sleep_hours": 9.0}, nothing_unusual=True
    )
    assert provenance == dict.fromkeys(tail, "assumed_stable")
    opened = resolve_filter_answer(
        calm_history, as_of, tail, {"sleep_hours": 2.0}, nothing_unusual=True
    )
    assert opened == {}


def test_closing_question_appears_only_when_the_outcome_is_unknown(calm_history):
    """The loop only closes once: no question when yesterday was already reported."""
    from ml.voi import closing_question

    as_of = last_date(calm_history)
    question, target = closing_question(calm_history, as_of)
    previous = as_of - timedelta(days=1)
    reported = any(
        log["date"] == previous.isoformat() and log.get("crisis_occurred") is not None
        for log in calm_history
    )
    if reported:
        assert question is None and target is None
    else:
        assert target == previous
        assert previous.isoformat() in question
