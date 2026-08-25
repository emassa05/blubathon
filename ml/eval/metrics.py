"""The metrics of SPEC 14.3, each with an explicit unsupported case.

Average precision comes from scikit-learn, not from a hand-rolled version whose
tie handling nobody has checked (CONVENTIONS 9.4). AUC is simply not computed
with one class, and calibration is a maximum-likelihood fit that reports
`not_estimable` rather than a number when it cannot converge.

Every function here returns `None` when the data does not support the estimate.
Zero is a value; the absence of an estimate is not.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
from scipy.optimize import minimize
from sklearn.metrics import average_precision_score, roc_auc_score

_PROBABILITY_FLOOR: Final = 1e-12
_CALIBRATION_MAX_ITERATIONS: Final = 500
_CALIBRATION_TOLERANCE: Final = 1e-10


def _validate(labels: Sequence[int], probabilities: Sequence[float]) -> None:
    if len(labels) != len(probabilities):
        raise ValueError("labels and probabilities must have the same length")
    for probability in probabilities:
        if not 0.0 <= probability <= 1.0 or math.isnan(probability):
            raise ValueError("a probability outside [0,1] is not a prediction")
    for label in labels:
        if label not in (0, 1):
            raise ValueError("a label is 0 or 1")


def has_both_classes(labels: Sequence[int]) -> bool:
    return 0 in labels and 1 in labels


def brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float | None:
    """`mean((p - y)^2)`. Defined per row, so one class is still fine."""

    _validate(labels, probabilities)
    if not labels:
        return None
    pairs = zip(labels, probabilities, strict=True)
    return float(np.mean([(probability - label) ** 2 for label, probability in pairs]))


def average_precision(labels: Sequence[int], probabilities: Sequence[float]) -> float | None:
    """scikit-learn's `average_precision_score`; `None` without both classes."""

    _validate(labels, probabilities)
    if not has_both_classes(labels):
        return None
    return float(average_precision_score(np.asarray(labels), np.asarray(probabilities)))


def auc_roc(labels: Sequence[int], probabilities: Sequence[float]) -> float | None:
    """Secondary to average precision, and never computed with one class."""

    _validate(labels, probabilities)
    if not has_both_classes(labels):
        return None
    return float(roc_auc_score(np.asarray(labels), np.asarray(probabilities)))


def logit(probability: float) -> float:
    clipped = min(max(probability, _PROBABILITY_FLOOR), 1.0 - _PROBABILITY_FLOOR)
    return math.log(clipped / (1.0 - clipped))


@dataclass(frozen=True, slots=True)
class CalibrationFit:
    """Intercept and slope of `y ~ a + b*logit(p)`, or why there are none."""

    estimable: bool
    intercept: float | None = None
    slope: float | None = None
    not_estimable_reason: str | None = None


def calibration_fit(labels: Sequence[int], probabilities: Sequence[float]) -> CalibrationFit:
    """Unpenalised maximum likelihood. One class or no convergence refuses."""

    _validate(labels, probabilities)
    if not has_both_classes(labels):
        return CalibrationFit(estimable=False, not_estimable_reason="single_class")
    if len(labels) < 3:
        return CalibrationFit(estimable=False, not_estimable_reason="insufficient_rows")

    x = np.asarray([logit(probability) for probability in probabilities], dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)

    def negative_log_likelihood(coefficients: np.ndarray) -> float:
        intercept, slope = coefficients
        eta = intercept + slope * x
        # log(1 + exp(eta)) written stably for large |eta|.
        stable = np.logaddexp(0.0, eta)
        return float(np.mean(stable - y * eta))

    result = minimize(
        negative_log_likelihood,
        x0=np.zeros(2, dtype=np.float64),
        method="L-BFGS-B",
        tol=_CALIBRATION_TOLERANCE,
        options={"maxiter": _CALIBRATION_MAX_ITERATIONS},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        return CalibrationFit(estimable=False, not_estimable_reason="convergence_failure")
    return CalibrationFit(estimable=True, intercept=float(result.x[0]), slope=float(result.x[1]))
