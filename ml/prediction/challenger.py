"""The preregistered logistic challenger (SPEC 8.4).

Two predictors, chosen before looking at the data, on top of the personal
baseline as a fixed offset:

    logit(p_t) = logit(p_base_t) + b0 + b1*sleep_deviation_t + b2*regulation_deviation_t

The offset carries coefficient 1, the intercept is not penalised, and `lambda`
is chosen by out-of-fold Brier with `LeaveOneGroupOut(subject_id)`. The point of
preregistering is that nothing here selects predictors from the data.

With the outcomes the repository has today the honest result is
`not_trainable_single_class`, and this module is built to say that rather than
to produce a number anyway.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

import numpy as np
from scipy.optimize import minimize

from ml.spec_constants import (
    CHALLENGER_L2_GRID,
    CHALLENGER_TIE_TOLERANCE,
    PERSONAL_DEVIATION_WINDOW_DAYS,
    PERSONAL_MIN_OBSERVATIONS,
)
from packages.shared.canonical import exclusive_window, in_window, local_date
from packages.shared.domain.observation import PRIMARY_REAL_MODEL_MODES, FieldObservation
from packages.shared.enums import (
    DailyRegulationState,
    FieldCode,
    NotTrainableReason,
    SleepQuality,
)
from packages.shared.projection import project_as_of, unique_active

CHALLENGER_MODEL_VERSION = "real-logit-challenger-0.3.0"
CHALLENGER_PROTOCOL_VERSION = "challenger-protocol-0.3.0"

# SPEC 8.4: fixed before the run and hashed into the training protocol, not
# per-run flags.
OPTIMIZER = "L-BFGS-B"
TOLERANCE = 1e-10
MAX_ITERATIONS = 500

_PROBABILITY_FLOOR = 1e-12

# SPEC 8.4. `other`, unknown, missing and conflicted all map to null: an
# unusable answer is not a zero.
SLEEP_DISRUPTED = {
    SleepQuality.INTERRUPTED.value: 1.0,
    SleepQuality.SLEEP_ONSET_DIFFICULTY.value: 1.0,
    SleepQuality.RESTORATIVE.value: 0.0,
}
REGULATION_FREQUENT = {
    DailyRegulationState.FREQUENT_DYSREGULATION.value: 1.0,
    DailyRegulationState.EXCELLENT.value: 0.0,
    DailyRegulationState.STABLE_WITH_SUPPORT.value: 0.0,
}
PREDICTOR_ENCODINGS = {
    FieldCode.SLEEP_QUALITY: SLEEP_DISRUPTED,
    FieldCode.DAILY_REGULATION_STATE: REGULATION_FREQUENT,
}


def logit(probability: float) -> float:
    clipped = min(max(probability, _PROBABILITY_FLOOR), 1.0 - _PROBABILITY_FLOOR)
    return math.log(clipped / (1.0 - clipped))


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def encode_predictor(field_code: FieldCode, value: object) -> float | None:
    """1, 0 or `None`. `other`, unknown and missing are all null (SPEC 8.4)."""

    encoding = PREDICTOR_ENCODINGS.get(field_code)
    if encoding is None:
        raise ValueError(f"{field_code} is not a preregistered challenger predictor")
    if not isinstance(value, str):
        return None
    return encoding.get(value)


@dataclass(frozen=True, slots=True)
class PersonalRate:
    """The subject's own previous rate of a predictor, or why there is none."""

    field_code: FieldCode
    rate: float | None
    n_days: int
    reason: str | None = None


def personal_predictor_rate(
    observations: Iterable[FieldObservation],
    *,
    tenant_id: UUID,
    subject_id: UUID,
    source: object,
    field_code: FieldCode,
    as_of_at: datetime,
    window_days: int = PERSONAL_DEVIATION_WINDOW_DAYS,
    minimum_days: int = PERSONAL_MIN_OBSERVATIONS,
) -> PersonalRate:
    """The previous rate over `[D-30, D)` for one subject, source and field.

    Sources are never combined and a conflict never becomes a zero (SPEC 8.4).
    """

    projection = project_as_of(observations, as_of_at)
    window = exclusive_window(local_date(as_of_at), window_days)
    scoped = [
        row
        for row in projection.leaves
        if (row.tenant_id, row.subject_id, row.source, row.field_code)
        == (tenant_id, subject_id, source, field_code)
        and in_window(row.local_date, window)
        and row.entry_mode in PRIMARY_REAL_MODEL_MODES
    ]
    grouped = unique_active(
        project_as_of(scoped, as_of_at),
        key=lambda row: (row.field_code, row.source, row.local_date),
    )
    if not grouped.is_clean:
        return PersonalRate(field_code=field_code, rate=None, n_days=0, reason="feature_conflict")

    encoded = [encode_predictor(field_code, row.value) for row in grouped.rows.values()]
    usable = [value for value in encoded if value is not None]
    if len(usable) < minimum_days:
        return PersonalRate(
            field_code=field_code,
            rate=None,
            n_days=len(usable),
            reason="personal_predictor_history_insufficient",
        )
    return PersonalRate(field_code=field_code, rate=sum(usable) / len(usable), n_days=len(usable))


@dataclass(frozen=True, slots=True)
class ChallengerRow:
    """One episode as the challenger sees it, already reduced to its features."""

    subject_id: UUID
    p_base: float
    sleep_deviation: float
    regulation_deviation: float
    label: int


def negative_log_likelihood(
    coefficients: Sequence[float], rows: Sequence[ChallengerRow], penalty: float
) -> float:
    """The SPEC 8.4 objective, written literally.

    Mean binary cross-entropy with the baseline logit as a fixed offset, plus
    `lambda/2 * (b1^2 + b2^2)`. The intercept is not penalised, there are no
    class weights and no extra standardisation.
    """

    intercept, beta_sleep, beta_regulation = coefficients
    total = 0.0
    for row in rows:
        eta = (
            logit(row.p_base)
            + intercept
            + beta_sleep * row.sleep_deviation
            + beta_regulation * row.regulation_deviation
        )
        probability = min(max(sigmoid(eta), _PROBABILITY_FLOOR), 1.0 - _PROBABILITY_FLOOR)
        total -= row.label * math.log(probability) + (1 - row.label) * math.log(1.0 - probability)
    return total / len(rows) + penalty / 2.0 * (beta_sleep**2 + beta_regulation**2)


@dataclass(frozen=True, slots=True)
class ChallengerFit:
    """The fitted coefficients, or a clean statement that there is no fit."""

    converged: bool
    intercept: float | None = None
    beta_sleep: float | None = None
    beta_regulation: float | None = None
    penalty: float | None = None
    iterations: int = 0
    message: str = ""

    def predict(self, row: ChallengerRow) -> float | None:
        if not self.converged or self.intercept is None:
            return None
        eta = (
            logit(row.p_base)
            + self.intercept
            + (self.beta_sleep or 0.0) * row.sleep_deviation
            + (self.beta_regulation or 0.0) * row.regulation_deviation
        )
        return sigmoid(eta)


def fit_challenger(rows: Sequence[ChallengerRow], *, penalty: float) -> ChallengerFit:
    """One L-BFGS-B fit at a fixed `lambda`, in float64."""

    if not rows:
        return ChallengerFit(converged=False, message="no rows")

    def objective(coefficients: np.ndarray) -> float:
        return negative_log_likelihood(coefficients.tolist(), rows, penalty)

    result = minimize(
        objective,
        x0=np.zeros(3, dtype=np.float64),
        method=OPTIMIZER,
        tol=TOLERANCE,
        options={"maxiter": MAX_ITERATIONS},
    )
    if not result.success:
        return ChallengerFit(converged=False, message=str(result.message))
    intercept, beta_sleep, beta_regulation = (float(value) for value in result.x)
    return ChallengerFit(
        converged=True,
        intercept=intercept,
        beta_sleep=beta_sleep,
        beta_regulation=beta_regulation,
        penalty=penalty,
        iterations=int(result.nit),
        message=str(result.message),
    )


@dataclass(frozen=True, slots=True)
class TrainabilityReport:
    """Whether a training run may proceed, and the reason when it may not."""

    trainable: bool
    reason: NotTrainableReason | None = None
    n_rows: int = 0
    n_subjects: int = 0
    n_positive: int = 0
    n_negative: int = 0
    detail: str = ""


def assess_trainability(rows: Sequence[ChallengerRow]) -> TrainabilityReport:
    """Both classes overall and in every training partition (SPEC 8.4, INV-19).

    A validation fold of a single subject may hold one class, because the
    per-row Brier is still defined; the aggregate out-of-fold set may not.
    """

    subjects = {row.subject_id for row in rows}
    positives = sum(row.label for row in rows)
    negatives = len(rows) - positives
    report = TrainabilityReport(
        trainable=False,
        n_rows=len(rows),
        n_subjects=len(subjects),
        n_positive=positives,
        n_negative=negatives,
    )

    if positives == 0 or negatives == 0:
        return replace(
            report,
            reason=NotTrainableReason.SINGLE_CLASS,
            detail="the eligible outcomes hold a single class",
        )
    if len(subjects) < 2:
        return replace(
            report,
            reason=NotTrainableReason.INSUFFICIENT_SAMPLE_PLAN,
            detail="LeaveOneGroupOut needs at least two subjects",
        )

    for held_out in subjects:
        training = [row for row in rows if row.subject_id != held_out]
        if {row.label for row in training} != {0, 1}:
            return replace(
                report,
                reason=NotTrainableReason.SINGLE_CLASS,
                detail=f"a training partition without subject {held_out} holds one class",
            )

    return replace(report, trainable=True)


@dataclass(frozen=True, slots=True)
class LambdaSelection:
    """The chosen penalty and the out-of-fold Brier that chose it."""

    penalty: float | None
    brier: float | None
    scores: tuple[tuple[float, float | None], ...]
    reason: NotTrainableReason | None = None


def select_penalty(
    rows: Sequence[ChallengerRow],
    *,
    grid: Sequence[float] = CHALLENGER_L2_GRID,
    tie_tolerance: float = CHALLENGER_TIE_TOLERANCE,
) -> LambdaSelection:
    """Lowest out-of-fold Brier over `LeaveOneGroupOut(subject_id)`.

    Every transformation, the personal rate included, is computed inside the
    fold at each row's own cutoff. Ties within `1e-12` pick the larger `lambda`,
    the more regularised model.
    """

    trainability = assess_trainability(rows)
    if not trainability.trainable:
        return LambdaSelection(penalty=None, brier=None, scores=(), reason=trainability.reason)

    subjects = sorted({row.subject_id for row in rows}, key=str)
    scores: list[tuple[float, float | None]] = []
    for penalty in grid:
        squared_errors: list[float] = []
        usable = True
        for held_out in subjects:
            training = [row for row in rows if row.subject_id != held_out]
            validation = [row for row in rows if row.subject_id == held_out]
            fit = fit_challenger(training, penalty=penalty)
            if not fit.converged:
                usable = False
                break
            for row in validation:
                predicted = fit.predict(row)
                if predicted is None:
                    usable = False
                    break
                squared_errors.append((predicted - row.label) ** 2)
            if not usable:
                break
        scores.append((penalty, None if not usable else sum(squared_errors) / len(squared_errors)))

    valid = [(penalty, brier) for penalty, brier in scores if brier is not None]
    if not valid:
        return LambdaSelection(
            penalty=None,
            brier=None,
            scores=tuple(scores),
            reason=NotTrainableReason.CONVERGENCE_FAILURE,
        )

    best = min(brier for _, brier in valid)
    tied = [penalty for penalty, brier in valid if brier - best <= tie_tolerance]
    chosen = max(tied)
    return LambdaSelection(
        penalty=chosen,
        brier=next(brier for penalty, brier in valid if penalty == chosen),
        scores=tuple(scores),
    )


@dataclass(frozen=True, slots=True)
class ChallengerTrainingResult:
    """A candidate artifact, or an honest reason no candidate exists."""

    trainable: bool
    reason: NotTrainableReason | None = None
    selection: LambdaSelection | None = None
    fit: ChallengerFit | None = None
    model_version: str = CHALLENGER_MODEL_VERSION
    protocol_version: str = CHALLENGER_PROTOCOL_VERSION
    detail: str = ""


def train_challenger(rows: Sequence[ChallengerRow]) -> ChallengerTrainingResult:
    """Select `lambda`, refit once on all eligible rows, and stop there.

    There is no automatic promotion: the artifact is a candidate, and the
    challenger stays in shadow for the whole of v0.3.
    """

    trainability = assess_trainability(rows)
    if not trainability.trainable:
        return ChallengerTrainingResult(
            trainable=False, reason=trainability.reason, detail=trainability.detail
        )

    selection = select_penalty(rows)
    if selection.penalty is None:
        return ChallengerTrainingResult(
            trainable=False,
            reason=selection.reason,
            selection=selection,
            detail="no penalty produced a usable out-of-fold score",
        )

    fit = fit_challenger(rows, penalty=selection.penalty)
    if not fit.converged:
        return ChallengerTrainingResult(
            trainable=False,
            reason=NotTrainableReason.CONVERGENCE_FAILURE,
            selection=selection,
            detail=fit.message,
        )
    return ChallengerTrainingResult(trainable=True, selection=selection, fit=fit)
