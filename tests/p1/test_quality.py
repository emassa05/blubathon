from __future__ import annotations

from datetime import date, timedelta

import pytest

from ml.features.quality import compute_icd
from ml.spec_constants import ICD_WEIGHTS

TARGET_DATE = date(2026, 8, 25)


def _record(
    day: date,
    *,
    source: str = "home",
    provenance: str = "observed",
    include_values: bool = True,
) -> dict[str, object]:
    values: dict[str, object] = {
        "sleep_hours": 8.0,
        "sleep_quality": 4,
        "night_awakenings": 1,
        "gi_status": 4,
        "routine_changes": False,
        "wake_state": 4,
        "dysregulation_events": 1,
        "morning_support_need": 2,
        "alertness": 3,
        "social_interactions": 4,
        "activity_participation": 4,
        "eating_status": 4,
        "food_changes": False,
        "relevant_event_flag": False,
        "crisis_occurred": False,
    }
    if not include_values:
        values = {variable: None for variable in values}
        values["crisis_occurred"] = False
    return {
        "date": day,
        "source": source,
        **values,
        "field_provenance": {variable: provenance for variable in ICD_WEIGHTS},
    }


def test_perfect_history_has_full_icd() -> None:
    history = [_record(TARGET_DATE - timedelta(days=offset)) for offset in range(14)]
    assert compute_icd(history, TARGET_DATE) == pytest.approx(
        {"icd": 1.0, "coverage": 1.0, "recency": 1.0, "consistency": 1.0}
    )


def test_empty_history_has_zero_icd() -> None:
    assert compute_icd([], TARGET_DATE) == {
        "icd": 0.0,
        "coverage": 0.0,
        "recency": 0.0,
        "consistency": 1.0,
    }


def test_assumed_stable_counts_half_as_much_as_observed() -> None:
    observed = compute_icd([_record(TARGET_DATE)], TARGET_DATE)
    assumed = compute_icd(
        [_record(TARGET_DATE, provenance="assumed_stable", include_values=False)], TARGET_DATE
    )
    assert assumed["coverage"] == pytest.approx(observed["coverage"] / 2)


@pytest.mark.parametrize(
    ("days_ago", "expected"),
    [(0, 1.0), (2, 0.5), (4, 0.25)],
)
def test_recency_has_two_day_half_life(days_ago: int, expected: float) -> None:
    history = [_record(TARGET_DATE - timedelta(days=days_ago))]
    assert compute_icd(history, TARGET_DATE)["recency"] == pytest.approx(expected)


def test_single_source_and_no_overlap_are_consistent() -> None:
    single_source = [_record(TARGET_DATE)]
    no_overlap = [
        {
            "date": TARGET_DATE,
            "source": "home",
            "sleep_hours": 8.0,
            "field_provenance": {"sleep_hours": "observed"},
        },
        {
            "date": TARGET_DATE,
            "source": "school",
            "social_interactions": 4,
            "field_provenance": {"social_interactions": "observed"},
        },
    ]
    assert compute_icd(single_source, TARGET_DATE)["consistency"] == 1.0
    assert compute_icd(no_overlap, TARGET_DATE)["consistency"] == 1.0


def test_overlapping_source_disagreement_is_penalized() -> None:
    history = [
        {
            "date": TARGET_DATE,
            "source": "home",
            "social_interactions": 1,
            "crisis_occurred": False,
            "field_provenance": {"social_interactions": "observed"},
        },
        {
            "date": TARGET_DATE,
            "source": "school",
            "social_interactions": 5,
            "crisis_occurred": False,
            "field_provenance": {"social_interactions": "observed"},
        },
    ]
    assert compute_icd(history, TARGET_DATE)["consistency"] == 0.5


def test_future_records_do_not_affect_quality() -> None:
    current = [_record(TARGET_DATE)]
    with_future = [*current, _record(TARGET_DATE + timedelta(days=1))]
    assert compute_icd(with_future, TARGET_DATE) == compute_icd(current, TARGET_DATE)


def test_all_components_remain_bounded() -> None:
    history = [_record(TARGET_DATE - timedelta(days=offset), source="home") for offset in range(5)]
    metrics = compute_icd(history, TARGET_DATE)
    assert all(0.0 <= value <= 1.0 for value in metrics.values())
