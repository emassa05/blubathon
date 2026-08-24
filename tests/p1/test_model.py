from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from ml.engine.model import RiskEnsemble, build_supervised_dataset, split_by_child
from ml.errors import ModelNotReadyError
from ml.spec_constants import (
    MODEL_CLASS_WEIGHT,
    MODEL_COLSAMPLE_BYTREE,
    MODEL_EARLY_STOPPING_ROUNDS,
    MODEL_ENSEMBLE_SEEDS,
    MODEL_INTERVAL_Z,
    MODEL_LEARNING_RATE,
    MODEL_MAX_DEPTH,
    MODEL_MIN_CHILD_SAMPLES,
    MODEL_N_ESTIMATORS,
    MODEL_NUM_LEAVES,
    MODEL_OBJECTIVE,
    MODEL_REG_LAMBDA,
    MODEL_SUBSAMPLE,
    RANDOM_SEED,
)


def test_child_split_is_deterministic_and_disjoint() -> None:
    child_ids = np.array([f"child-{index:03d}" for index in range(200)])
    first = split_by_child(child_ids)
    second = split_by_child(child_ids)
    assert first == second
    assert (len(first.train), len(first.validation), len(first.test)) == (120, 40, 40)
    assert first.train.isdisjoint(first.validation)
    assert first.train.isdisjoint(first.test)
    assert first.validation.isdisjoint(first.test)


def test_supervised_dataset_uses_exact_next_calendar_day() -> None:
    start = date(2026, 8, 1)
    logs = pd.DataFrame(
        [
            {
                "child_id": "child-a",
                "date": start + timedelta(days=offset),
                "source": "home",
                "sleep_hours": 8.0 - offset,
                "crisis_occurred": offset == 2,
            }
            for offset in range(4)
        ]
    )
    dataset = build_supervised_dataset(logs)
    assert list(dataset.dates.date) == [start, start + timedelta(days=1), start + timedelta(days=2)]
    assert dataset.target.tolist() == [0, 1, 0]
    assert len(dataset.features) == 3


@pytest.fixture(scope="module")
def fitted_model() -> tuple[
    RiskEnsemble,
    pd.DataFrame,
    np.ndarray,
    np.ndarray,
    pd.DatetimeIndex,
]:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, float]] = []
    target: list[int] = []
    child_ids: list[str] = []
    dates: list[date] = []
    for child_index in range(100):
        for day in range(12):
            signal = float(day)
            outcome = int(day >= 9)
            rows.append(
                {
                    "sleep_hours": np.nan if day % 3 == 0 else 9.0 - outcome * 4.0,
                    "signal": signal + rng.normal(0.0, 0.05),
                    "dysregulation_events": float(rng.integers(0, 2)),
                }
            )
            target.append(outcome)
            child_ids.append(f"child-{child_index:02d}")
            dates.append(date(2026, 8, 1) + timedelta(days=day))
    features = pd.DataFrame(rows)
    target_array = np.asarray(target)
    child_array = np.asarray(child_ids)
    model = RiskEnsemble().fit(features, target_array, child_array)
    return model, features, target_array, child_array, pd.DatetimeIndex(dates)


def test_model_uses_fixed_lightgbm_configuration() -> None:
    parameters = RiskEnsemble().model_parameters()
    assert parameters["n_estimators"] == MODEL_N_ESTIMATORS
    assert parameters["learning_rate"] == MODEL_LEARNING_RATE
    assert parameters["num_leaves"] == MODEL_NUM_LEAVES
    assert parameters["max_depth"] == MODEL_MAX_DEPTH
    assert parameters["min_child_samples"] == MODEL_MIN_CHILD_SAMPLES
    assert parameters["subsample"] == MODEL_SUBSAMPLE
    assert parameters["colsample_bytree"] == MODEL_COLSAMPLE_BYTREE
    assert parameters["reg_lambda"] == MODEL_REG_LAMBDA
    assert parameters["class_weight"] == MODEL_CLASS_WEIGHT
    assert parameters["random_state"] == RANDOM_SEED
    assert parameters["objective"] == MODEL_OBJECTIVE


def test_unfitted_model_rejects_prediction() -> None:
    with pytest.raises(ModelNotReadyError):
        RiskEnsemble().predict(pd.DataFrame({"sleep_hours": [8.0]}))


def test_ensemble_trains_twenty_seeded_members_with_native_nan(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, _, _, _, _ = fitted_model
    assert [member.seed for member in model.members_] == list(MODEL_ENSEMBLE_SEEDS)
    assert all(member.fit_input_had_nan for member in model.members_)
    assert model.calibration_children_.isdisjoint(model.conformal_children_)
    assert model.calibration_children_ | model.conformal_children_ == model.split_.validation
    assert all(
        set(member.bootstrap_children).issubset(model.split_.train)
        and member.early_stopping_children.isdisjoint(member.bootstrap_children)
        for member in model.members_
    )


def test_predictions_include_calibrated_80_percent_interval(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, features, _, _, _ = fitted_model
    prediction = model.predict(features.iloc[:20])
    distribution = model.predict_distribution(features.iloc[:20])
    assert np.all((prediction.probability >= 0.0) & (prediction.probability <= 1.0))
    assert np.all(prediction.lower <= prediction.probability)
    assert np.all(prediction.probability <= prediction.upper)
    assert np.allclose(prediction.width, prediction.upper - prediction.lower)
    assert distribution.shape == (20, 20)
    assert np.allclose(prediction.probability, distribution.mean(axis=1))
    assert np.allclose(prediction.standard_deviation, distribution.std(axis=1))
    assert np.allclose(
        prediction.lower,
        np.clip(
            prediction.probability - MODEL_INTERVAL_Z * prediction.standard_deviation,
            0.0,
            1.0,
        ),
    )
    assert all(0 < member.model.best_iteration_ <= MODEL_N_ESTIMATORS for member in model.members_)
    assert MODEL_EARLY_STOPPING_ROUNDS == 40


def test_model_beats_mandatory_baselines(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, features, target, child_ids, _ = fitted_model
    metrics = model.evaluate(features, target, child_ids)
    assert metrics["auc_pr"] > metrics["base_rate_auc_pr"]
    assert metrics["auc_pr"] > metrics["previous_dysregulation_auc_pr"]
    assert metrics["previous_dysregulation_coverage"] == 1.0


def test_mapie_conformal_report_is_available(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, features, target, child_ids, _ = fitted_model
    test_mask = np.isin(child_ids, list(model.split_.test))
    report = model.conformal_report(features.loc[test_mask], target[test_mask])
    assert report["confidence_level"] == 0.9
    assert 0.0 <= report["coverage"] <= 1.0
    assert 0.0 <= report["mean_set_size"] <= 2.0


def test_temporal_holdout_reports_final_child_days(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, features, target, child_ids, dates = fitted_model
    metrics = model.evaluate_temporal_holdout(features, target, child_ids, dates)
    assert 0.0 <= metrics["auc_pr"] <= 1.0


def test_ensemble_is_reproducible(
    fitted_model: tuple[RiskEnsemble, pd.DataFrame, np.ndarray, np.ndarray, pd.DatetimeIndex],
) -> None:
    model, features, target, child_ids, _ = fitted_model
    repeated = RiskEnsemble().fit(features, target, child_ids)
    assert np.allclose(
        model.predict(features.iloc[:30]).probability,
        repeated.predict(features.iloc[:30]).probability,
    )
