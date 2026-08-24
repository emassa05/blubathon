"""Calibrated LightGBM bootstrap ensemble from SPEC sections 9.2-9.4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from mapie.classification import SplitConformalClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ml.errors import ContractViolationError, ModelNotReadyError
from ml.features import build_feature_matrix
from ml.spec_constants import (
    MODEL_CALIBRATION_FRACTION,
    MODEL_CLASS_WEIGHT,
    MODEL_COLSAMPLE_BYTREE,
    MODEL_CONFORMAL_CONFIDENCE,
    MODEL_EARLY_STOPPING_ROUNDS,
    MODEL_ENSEMBLE_SEEDS,
    MODEL_INTERVAL_Z,
    MODEL_LEARNING_RATE,
    MODEL_MAX_DEPTH,
    MODEL_MIN_CHILD_SAMPLES,
    MODEL_MIN_CONFORMAL_SAMPLES,
    MODEL_MIN_SPLIT_CHILDREN,
    MODEL_N_ESTIMATORS,
    MODEL_NUM_LEAVES,
    MODEL_OBJECTIVE,
    MODEL_REG_LAMBDA,
    MODEL_SUBSAMPLE,
    MODEL_TEMPORAL_HOLDOUT_DAYS,
    MODEL_TRAIN_FRACTION,
    MODEL_VALIDATION_FRACTION,
    PREDICTION_HORIZON_DAYS,
    RANDOM_SEED,
    RISK_MAX,
    RISK_MIN,
)


@dataclass(frozen=True)
class SupervisedDataset:
    features: pd.DataFrame
    target: np.ndarray
    child_ids: np.ndarray
    dates: pd.DatetimeIndex


@dataclass(frozen=True)
class ChildSplit:
    train: frozenset[str]
    validation: frozenset[str]
    test: frozenset[str]


@dataclass(frozen=True)
class EnsemblePrediction:
    probability: np.ndarray
    standard_deviation: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    width: np.ndarray


@dataclass(frozen=True)
class _EnsembleMember:
    model: lgb.LGBMClassifier
    calibrator: IsotonicRegression
    seed: int
    fit_input_had_nan: bool
    bootstrap_children: tuple[str, ...]
    early_stopping_children: frozenset[str]

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        raw_probability = self.model.predict_proba(features)[:, 1]
        return np.clip(self.calibrator.predict(raw_probability), RISK_MIN, RISK_MAX)


def split_by_child(child_ids: np.ndarray | pd.Series, seed: int = RANDOM_SEED) -> ChildSplit:
    """Create deterministic, mutually exclusive 60/20/20 child partitions."""
    unique_children = np.array(sorted({str(child_id) for child_id in child_ids}))
    if len(unique_children) < MODEL_MIN_SPLIT_CHILDREN:
        raise ContractViolationError(
            f"at least {MODEL_MIN_SPLIT_CHILDREN} children are required for a split"
        )
    shuffled = np.random.default_rng(seed).permutation(unique_children)
    train_end = int(len(shuffled) * MODEL_TRAIN_FRACTION)
    validation_end = train_end + int(len(shuffled) * MODEL_VALIDATION_FRACTION)
    return ChildSplit(
        train=frozenset(shuffled[:train_end]),
        validation=frozenset(shuffled[train_end:validation_end]),
        test=frozenset(shuffled[validation_end:]),
    )


def build_supervised_dataset(logs: pd.DataFrame) -> SupervisedDataset:
    """Pair features through day t with the crisis target on calendar day t+1."""
    matrix = build_feature_matrix(logs)
    if matrix.empty:
        raise ContractViolationError("cannot build a supervised dataset from empty logs")

    targets = logs.copy()
    targets["date"] = pd.to_datetime(targets["date"]).dt.normalize()
    targets = (
        targets.groupby(["child_id", "date"], as_index=False)["crisis_occurred"]
        .max()
        .rename(columns={"crisis_occurred": "target"})
    )
    targets["date"] = targets["date"] - np.timedelta64(PREDICTION_HORIZON_DAYS, "D")
    paired = matrix.merge(targets, on=["child_id", "date"], how="inner", validate="one_to_one")
    paired = paired[paired["target"].notna()].sort_values(["child_id", "date"], ignore_index=True)
    metadata_columns = {"child_id", "date", "target"}
    feature_columns = [column for column in paired.columns if column not in metadata_columns]
    features = paired[feature_columns].apply(pd.to_numeric, errors="coerce").astype(float)
    return SupervisedDataset(
        features=features,
        target=paired["target"].astype(int).to_numpy(),
        child_ids=paired["child_id"].astype(str).to_numpy(),
        dates=pd.DatetimeIndex(paired["date"]),
    )


def _classifier(seed: int) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        objective=MODEL_OBJECTIVE,
        n_estimators=MODEL_N_ESTIMATORS,
        learning_rate=MODEL_LEARNING_RATE,
        num_leaves=MODEL_NUM_LEAVES,
        max_depth=MODEL_MAX_DEPTH,
        min_child_samples=MODEL_MIN_CHILD_SAMPLES,
        subsample=MODEL_SUBSAMPLE,
        colsample_bytree=MODEL_COLSAMPLE_BYTREE,
        reg_lambda=MODEL_REG_LAMBDA,
        class_weight=MODEL_CLASS_WEIGHT,
        random_state=seed,
        verbosity=-1,
    )


class _EnsembleClassifier(ClassifierMixin, BaseEstimator):
    """Scikit-learn adapter used only by MAPIE's prefit conformal layer."""

    def __init__(self, ensemble: RiskEnsemble) -> None:
        self.ensemble = ensemble
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = len(ensemble.feature_names_)

    def __sklearn_is_fitted__(self) -> bool:
        return True

    def predict_proba(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        frame = (
            features
            if isinstance(features, pd.DataFrame)
            else pd.DataFrame(features, columns=self.ensemble.feature_names_)
        )
        probability = self.ensemble.predict(frame).probability
        return np.column_stack((RISK_MAX - probability, probability))

    def predict(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(features), axis=1)


class RiskEnsemble:
    """Child-bootstrap LightGBM ensemble with isotonic and conformal calibration."""

    def __init__(self) -> None:
        self.members_: list[_EnsembleMember] = []
        self.feature_names_: list[str] = []
        self.split_: ChildSplit | None = None
        self.conformal_: SplitConformalClassifier | None = None
        self.training_base_rate_: float | None = None
        self.calibration_children_: frozenset[str] = frozenset()
        self.conformal_children_: frozenset[str] = frozenset()

    @property
    def is_fitted(self) -> bool:
        return len(self.members_) == len(MODEL_ENSEMBLE_SEEDS)

    def _validate_features(self, features: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise ModelNotReadyError("the risk ensemble has not been fitted")
        missing = set(self.feature_names_) - set(features.columns)
        if missing:
            names = ", ".join(sorted(missing))
            raise ContractViolationError(f"missing model features: {names}")
        return features[self.feature_names_]

    def fit(
        self,
        features: pd.DataFrame,
        target: np.ndarray | pd.Series,
        child_ids: np.ndarray | pd.Series,
    ) -> RiskEnsemble:
        """Fit 20 child-level bootstrap members and their validation calibrators."""
        if not (len(features) == len(target) == len(child_ids)):
            raise ContractViolationError("features, target, and child_ids must have equal length")
        features = features.reset_index(drop=True)
        target_array = np.asarray(target, dtype=int)
        child_array = np.asarray(child_ids, dtype=str)
        self.feature_names_ = list(features.columns)
        self.split_ = split_by_child(child_array)
        train_mask = np.isin(child_array, list(self.split_.train))
        self.training_base_rate_ = float(target_array[train_mask].mean())

        validation_children = np.random.default_rng(RANDOM_SEED).permutation(
            sorted(self.split_.validation)
        )
        calibration_end = max(
            1,
            int(len(validation_children) * MODEL_CALIBRATION_FRACTION),
        )
        self.calibration_children_ = frozenset(validation_children[:calibration_end])
        self.conformal_children_ = frozenset(validation_children[calibration_end:])
        if len(self.conformal_children_) < MODEL_MIN_CONFORMAL_SAMPLES:
            raise ContractViolationError(
                f"conformal calibration requires at least {MODEL_MIN_CONFORMAL_SAMPLES} children"
            )
        calibration_mask = np.isin(child_array, list(self.calibration_children_))
        calibration_features = features.loc[calibration_mask, self.feature_names_]
        calibration_target = target_array[calibration_mask]

        rows_by_child = {
            child_id: np.flatnonzero((child_array == child_id) & train_mask)
            for child_id in self.split_.train
        }
        train_children = np.array(sorted(self.split_.train))
        self.members_ = []
        for seed in MODEL_ENSEMBLE_SEEDS:
            sampled_children = np.random.default_rng(seed).choice(
                train_children,
                size=len(train_children),
                replace=True,
            )
            bootstrap_rows = np.concatenate(
                [rows_by_child[child_id] for child_id in sampled_children]
            )
            early_stopping_children = frozenset(self.split_.train - set(sampled_children))
            if not early_stopping_children:
                held_out_child = sampled_children[0]
                early_stopping_children = frozenset({held_out_child})
                bootstrap_rows = bootstrap_rows[child_array[bootstrap_rows] != held_out_child]
            early_stopping_mask = np.isin(child_array, list(early_stopping_children))
            early_stopping_features = features.loc[early_stopping_mask, self.feature_names_]
            early_stopping_target = target_array[early_stopping_mask]
            bootstrap_features = features.iloc[bootstrap_rows][self.feature_names_]
            bootstrap_target = target_array[bootstrap_rows]
            model = _classifier(seed)
            model.fit(
                bootstrap_features,
                bootstrap_target,
                eval_X=early_stopping_features,
                eval_y=early_stopping_target,
                eval_metric="binary_logloss",
                callbacks=[
                    lgb.early_stopping(
                        MODEL_EARLY_STOPPING_ROUNDS,
                        verbose=False,
                    )
                ],
            )
            validation_probability = model.predict_proba(calibration_features)[:, 1]
            calibrator = IsotonicRegression(out_of_bounds="clip").fit(
                validation_probability,
                calibration_target,
            )
            self.members_.append(
                _EnsembleMember(
                    model=model,
                    calibrator=calibrator,
                    seed=seed,
                    fit_input_had_nan=bool(bootstrap_features.isna().any().any()),
                    bootstrap_children=tuple(str(child) for child in sampled_children),
                    early_stopping_children=early_stopping_children,
                )
            )

        conformal_estimator = _EnsembleClassifier(self)
        self.conformal_ = SplitConformalClassifier(
            estimator=conformal_estimator,
            confidence_level=MODEL_CONFORMAL_CONFIDENCE,
            prefit=True,
            random_state=RANDOM_SEED,
        )
        conformal_rng = np.random.default_rng(RANDOM_SEED)
        conformal_rows = np.array(
            [
                conformal_rng.choice(np.flatnonzero(child_array == child_id))
                for child_id in sorted(self.conformal_children_)
            ]
        )
        self.conformal_.conformalize(
            features.iloc[conformal_rows][self.feature_names_],
            target_array[conformal_rows],
        )
        return self

    def predict_distribution(self, features: pd.DataFrame) -> np.ndarray:
        """Return calibrated probabilities with shape rows x ensemble members."""
        validated = self._validate_features(features)
        return np.column_stack([member.predict(validated) for member in self.members_])

    def predict(self, features: pd.DataFrame) -> EnsemblePrediction:
        predictions = self.predict_distribution(features)
        probability = predictions.mean(axis=1)
        standard_deviation = predictions.std(axis=1)
        lower = np.clip(probability - MODEL_INTERVAL_Z * standard_deviation, RISK_MIN, RISK_MAX)
        upper = np.clip(probability + MODEL_INTERVAL_Z * standard_deviation, RISK_MIN, RISK_MAX)
        return EnsemblePrediction(
            probability=probability,
            standard_deviation=standard_deviation,
            lower=lower,
            upper=upper,
            width=upper - lower,
        )

    def conformal_report(
        self,
        features: pd.DataFrame,
        target: np.ndarray | pd.Series,
    ) -> dict[str, float]:
        """Report MAPIE 90% prediction-set coverage and mean set size."""
        if self.conformal_ is None:
            raise ModelNotReadyError("the conformal classifier has not been fitted")
        validated = self._validate_features(features)
        target_array = np.asarray(target, dtype=int)
        if len(validated) != len(target_array):
            raise ContractViolationError("features and target must have equal length")
        if not len(target_array):
            raise ContractViolationError("conformal reporting requires at least one row")
        _, prediction_sets = self.conformal_.predict_set(validated)
        if prediction_sets.ndim == 3:
            prediction_sets = prediction_sets[:, :, 0]
        covered = prediction_sets[np.arange(len(target_array)), target_array]
        return {
            "confidence_level": MODEL_CONFORMAL_CONFIDENCE,
            "coverage": float(np.mean(covered)),
            "mean_set_size": float(np.mean(prediction_sets.sum(axis=1))),
        }

    def _evaluate_rows(
        self, test_features: pd.DataFrame, test_target: np.ndarray
    ) -> dict[str, float]:
        if not len(test_target):
            raise ContractViolationError("evaluation requires at least one held-out row")
        if not set(np.unique(test_target)).issubset({0, 1}):
            raise ContractViolationError("evaluation target must be binary")
        probability = self.predict(test_features).probability
        base_rate_probability = np.full(len(test_target), self.training_base_rate_)
        dysregulation_is_observed = test_features["dysregulation_events"].notna().to_numpy()
        previous_dysregulation = (
            test_features.loc[dysregulation_is_observed, "dysregulation_events"]
            .gt(RISK_MIN)
            .astype(float)
        )
        eligible_target = test_target[dysregulation_is_observed]
        auc_roc = (
            float(roc_auc_score(test_target, probability))
            if len(np.unique(test_target)) > 1
            else float("nan")
        )
        previous_auc_pr = (
            float(average_precision_score(eligible_target, previous_dysregulation))
            if len(eligible_target)
            else float("nan")
        )
        return {
            "auc_pr": float(average_precision_score(test_target, probability)),
            "auc_roc": auc_roc,
            "brier": float(brier_score_loss(test_target, probability)),
            "base_rate": float(test_target.mean()),
            "base_rate_auc_pr": float(average_precision_score(test_target, base_rate_probability)),
            "previous_dysregulation_auc_pr": previous_auc_pr,
            "previous_dysregulation_coverage": float(dysregulation_is_observed.mean()),
        }

    def evaluate(
        self,
        features: pd.DataFrame,
        target: np.ndarray | pd.Series,
        child_ids: np.ndarray | pd.Series,
    ) -> dict[str, float]:
        """Evaluate all held-out child rows against both mandatory baselines."""
        if self.split_ is None:
            raise ModelNotReadyError("the risk ensemble has not been fitted")
        if not (len(features) == len(target) == len(child_ids)):
            raise ContractViolationError("evaluation inputs must have equal length")
        child_array = np.asarray(child_ids, dtype=str)
        target_array = np.asarray(target, dtype=int)
        test_mask = np.isin(child_array, list(self.split_.test))
        return self._evaluate_rows(
            features.loc[test_mask].reset_index(drop=True),
            target_array[test_mask],
        )

    def evaluate_temporal_holdout(
        self,
        features: pd.DataFrame,
        target: np.ndarray | pd.Series,
        child_ids: np.ndarray | pd.Series,
        dates: pd.DatetimeIndex | np.ndarray | pd.Series,
    ) -> dict[str, float]:
        """Evaluate the final 30 calendar days of each held-out child."""
        if self.split_ is None:
            raise ModelNotReadyError("the risk ensemble has not been fitted")
        if not (len(features) == len(target) == len(child_ids) == len(dates)):
            raise ContractViolationError("temporal evaluation inputs must have equal length")
        child_array = np.asarray(child_ids, dtype=str)
        target_array = np.asarray(target, dtype=int)
        date_array = pd.DatetimeIndex(dates)
        temporal_mask = np.zeros(len(features), dtype=bool)
        for child_id in self.split_.test:
            child_mask = child_array == child_id
            if not child_mask.any():
                continue
            cutoff = date_array[child_mask].max() - pd.DateOffset(
                days=MODEL_TEMPORAL_HOLDOUT_DAYS - PREDICTION_HORIZON_DAYS
            )
            temporal_mask |= child_mask & (date_array >= cutoff)
        return self._evaluate_rows(
            features.loc[temporal_mask].reset_index(drop=True),
            target_array[temporal_mask],
        )

    def model_parameters(self) -> dict[str, Any]:
        """Expose the fixed LightGBM configuration for audit and tests."""
        return _classifier(RANDOM_SEED).get_params()
