from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from ml.features.baseline import (
    build_feature_matrix,
    compute_robust_mahalanobis,
    compute_robust_zscore,
)

CHILD_ID = "10000000-0000-4000-8000-000000000000"
START_DATE = date(2026, 7, 1)


def _history(values: list[float | None], variable: str = "sleep_hours") -> list[dict[str, object]]:
    return [
        {
            "child_id": CHILD_ID,
            "date": START_DATE + timedelta(days=index),
            "source": "home",
            variable: value,
            "crisis_occurred": False,
        }
        for index, value in enumerate(values)
    ]


def test_constant_history_has_zero_robust_zscore() -> None:
    history = _history([8.0] * 10)
    target = START_DATE + timedelta(days=10)
    assert compute_robust_zscore(history, "sleep_hours", target, 8.0) == 0.0


def test_fewer_than_five_observations_returns_nan() -> None:
    history = _history([8.0, None, 8.0, None, 8.0])
    target = START_DATE + timedelta(days=5)
    assert np.isnan(compute_robust_zscore(history, "sleep_hours", target, 7.0))


def test_large_personal_deviation_exceeds_anomaly_threshold() -> None:
    history = _history([7.0, 8.0, 9.0, 7.5, 8.5, 8.0, 7.0, 9.0])
    target = START_DATE + timedelta(days=8)
    assert abs(compute_robust_zscore(history, "sleep_hours", target, 11.0)) > 2.0


def test_recent_fourteen_day_regime_is_preferred() -> None:
    history = _history([0.0] * 16 + [10.0] * 14)
    target = START_DATE + timedelta(days=30)
    assert compute_robust_zscore(history, "sleep_hours", target, 10.0) == 0.0


def test_single_same_weekday_value_does_not_override_personal_median() -> None:
    history = _history([20.0] + [8.0] * 6)
    target = START_DATE + timedelta(days=7)
    assert compute_robust_zscore(history, "sleep_hours", target, 8.0) == 0.0


def test_robust_mahalanobis_separates_outlier() -> None:
    rng = np.random.default_rng(42)
    history = pd.DataFrame(
        {
            "child_id": CHILD_ID,
            "date": [START_DATE + timedelta(days=index) for index in range(40)],
            "sleep_hours": rng.normal(8.0, 0.3, 40),
            "gi_status": rng.normal(4.0, 0.2, 40),
        }
    )
    target = START_DATE + timedelta(days=40)
    normal = compute_robust_mahalanobis(
        history,
        CHILD_ID,
        target,
        {"sleep_hours": 8.0, "gi_status": 4.0},
        ("sleep_hours", "gi_status"),
    )
    outlier = compute_robust_mahalanobis(
        history,
        CHILD_ID,
        target,
        {"sleep_hours": 5.0, "gi_status": 1.0},
        ("sleep_hours", "gi_status"),
    )
    assert outlier > normal
    assert outlier > 2.0


def test_mahalanobis_handles_constant_history() -> None:
    history = pd.DataFrame(
        {
            "child_id": [CHILD_ID] * 10,
            "date": [START_DATE + timedelta(days=index) for index in range(10)],
            "sleep_hours": [8.0] * 10,
            "gi_status": [4.0] * 10,
        }
    )
    target = START_DATE + timedelta(days=10)
    normal = compute_robust_mahalanobis(
        history,
        CHILD_ID,
        target,
        {"sleep_hours": 8.0, "gi_status": 4.0},
        ("sleep_hours", "gi_status"),
    )
    outlier = compute_robust_mahalanobis(
        history,
        CHILD_ID,
        target,
        {"sleep_hours": 11.0, "gi_status": 1.0},
        ("sleep_hours", "gi_status"),
    )
    assert normal == 0.0
    assert outlier > 2.0


def test_mahalanobis_ignores_future_and_other_children() -> None:
    history = pd.DataFrame(
        {
            "child_id": [CHILD_ID] * 10,
            "date": [START_DATE + timedelta(days=index) for index in range(10)],
            "sleep_hours": np.linspace(7.0, 9.0, 10),
            "gi_status": np.linspace(3.0, 5.0, 10),
        }
    )
    target = START_DATE + timedelta(days=10)
    current = {"sleep_hours": 8.0, "gi_status": 4.0}
    original = compute_robust_mahalanobis(
        history, CHILD_ID, target, current, ("sleep_hours", "gi_status")
    )
    unrelated = history.assign(
        child_id="20000000-0000-4000-8000-000000000000",
        date=lambda frame: frame["date"] + timedelta(days=20),
        sleep_hours=20.0,
        gi_status=1.0,
    )
    extended = pd.concat([history, unrelated], ignore_index=True)
    assert compute_robust_mahalanobis(
        extended, CHILD_ID, target, current, ("sleep_hours", "gi_status")
    ) == pytest.approx(original)


def test_feature_matrix_preserves_missing_values_and_indicators() -> None:
    matrix = build_feature_matrix(_history([8.0, None, 7.5, 8.5, 8.0, 7.0]))
    missing_row = matrix.iloc[1]
    assert np.isnan(missing_row["sleep_hours"])
    assert bool(missing_row["sleep_hours_missing"])
    assert not bool(matrix.iloc[0]["sleep_hours_missing"])


def test_lags_use_calendar_days() -> None:
    history = _history([8.0, 7.0, 6.0])
    history.pop(1)
    matrix = build_feature_matrix(history)
    third_day = matrix.iloc[1]
    assert np.isnan(third_day["sleep_hours_lag_1d"])
    assert third_day["sleep_hours_lag_2d"] == 8.0


def test_features_include_required_windows_and_globals() -> None:
    matrix = build_feature_matrix(_history([8.0, 7.0, 6.0, 7.0, 8.0, 9.0, 8.0]))
    expected = {
        "sleep_hours",
        "sleep_hours_z",
        "sleep_hours_missing",
        "sleep_hours_lag_1d",
        "sleep_hours_lag_2d",
        "sleep_hours_mean_3d",
        "sleep_hours_mean_7d",
        "sleep_hours_trend_7d",
        "personal_base_rate",
        "day_of_week",
        "dysregulation_events_mean_3d",
    }
    assert expected.issubset(matrix.columns)
    assert not any("provenance" in column for column in matrix.columns)
    assert "food_changes_z" not in matrix.columns


def test_future_values_do_not_change_past_features() -> None:
    history = _history([8.0, 7.0, 6.0, 7.0, 8.0, 9.0])
    original = build_feature_matrix(history)
    history.append(
        {
            "child_id": CHILD_ID,
            "date": START_DATE + timedelta(days=6),
            "source": "home",
            "sleep_hours": 2.0,
            "crisis_occurred": True,
        }
    )
    extended = build_feature_matrix(history)
    pd.testing.assert_frame_equal(original, extended.iloc[:-1].reset_index(drop=True))


def test_rolling_features_do_not_replace_raw_nan() -> None:
    matrix = build_feature_matrix(_history([8.0, None, 6.0]))
    assert np.isnan(matrix.iloc[1]["sleep_hours"])
    assert matrix.iloc[1]["sleep_hours_mean_3d"] == pytest.approx(8.0)


def test_rolling_windows_trend_and_personal_rate_are_point_in_time() -> None:
    history = _history([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    history[1]["crisis_occurred"] = True
    matrix = build_feature_matrix(history)
    last = matrix.iloc[-1]
    assert last["sleep_hours_mean_3d"] == pytest.approx(6.0)
    assert last["sleep_hours_mean_7d"] == pytest.approx(4.0)
    assert last["sleep_hours_trend_7d"] == pytest.approx(1.0)
    assert last["personal_base_rate"] == pytest.approx(1 / 7)
