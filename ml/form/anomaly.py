"""When the full queue opens (SPEC 6.11).

Any one of six conditions opens it. Four are direct readings of today's answers;
two are statistical, and both of them refuse rather than invent when the history
is too thin.

The cuts 0.05 and 2.0 are product policy for opening a form. They are not
clinical thresholds and nothing here diagnoses anything.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import median

from ml.defaults.window import EligibleHistory, Stratum
from ml.spec_constants import (
    CATEGORICAL_ANOMALY_PROBABILITY,
    DEFAULT_PRIOR_PER_CATEGORY,
    MAD_TO_SIGMA,
    PERSONAL_DEVIATION_WINDOW_DAYS,
    PERSONAL_MIN_OBSERVATIONS,
    ROBUST_Z_ANOMALY,
)
from packages.shared.canonical import exclusive_window, in_window, local_date
from packages.shared.domain.observation import PRIMARY_REAL_MODEL_MODES, FieldObservation
from packages.shared.enums import (
    Alertness,
    DailyRegulationState,
    FieldCode,
    FormAnomalyTrigger,
    MedicationAdherence,
)
from packages.shared.field_catalog import FieldValue, closed_support
from packages.shared.projection import project_as_of, unique_active

ALERTNESS_EXTREMES = frozenset({Alertness.LOW.value, Alertness.HIGH.value})
OTHER_VALUE = "other"


@dataclass(frozen=True, slots=True)
class RobustDeviation:
    """Median, MAD and the z-score, or an explicit reason there is none."""

    field_code: FieldCode
    robust_z: float | None
    median: float | None
    mad: float | None
    n_observations: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CategoricalSurprise:
    """Posterior predictive probability of today's category, when it exists."""

    field_code: FieldCode
    probability: float | None
    n_observations: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class FormAnomaly:
    """Whether the queue opens, and every trigger that fired."""

    opens_queue: bool
    triggers: tuple[FormAnomalyTrigger, ...]
    deviations: tuple[RobustDeviation, ...] = ()
    surprises: tuple[CategoricalSurprise, ...] = ()


def compute_robust_deviation(
    observations: Iterable[FieldObservation],
    *,
    stratum: Stratum,
    current_value: float | int | None,
    as_of_at: datetime,
    window_days: int = PERSONAL_DEVIATION_WINDOW_DAYS,
    minimum: int = PERSONAL_MIN_OBSERVATIONS,
) -> RobustDeviation:
    """`robust_z = (x - median) / (1.4826 * MAD)` over `[D-30, D)` (SPEC 6.11).

    The factor is `1 / NormalPPF(0.75)`, which makes the MAD comparable to a
    standard deviation under a normal distribution. It does not make the data
    normal. With fewer than five values, a zero MAD, or no current value, there
    is no z-score and the queue does not open on this rule.
    """

    field_code = stratum.field_code
    if current_value is None:
        return RobustDeviation(
            field_code=field_code,
            robust_z=None,
            median=None,
            mad=None,
            n_observations=0,
            reason="no_current_value",
        )

    projection = project_as_of(observations, as_of_at)
    window = exclusive_window(local_date(as_of_at), window_days)
    scoped = [
        row
        for row in projection.leaves
        if (row.tenant_id, row.subject_id, row.source, row.field_code)
        == (stratum.tenant_id, stratum.subject_id, stratum.source, stratum.field_code)
        and in_window(row.local_date, window)
        and row.entry_mode in PRIMARY_REAL_MODEL_MODES
        and row.value is not None
    ]
    grouped = unique_active(
        project_as_of(scoped, as_of_at),
        key=lambda row: (row.field_code, row.source, row.local_date),
    )
    if not grouped.is_clean:
        return RobustDeviation(
            field_code=field_code,
            robust_z=None,
            median=None,
            mad=None,
            n_observations=0,
            reason="conflict",
        )

    history = [float(row.value) for row in grouped.rows.values()]  # type: ignore[arg-type]
    if len(history) < minimum:
        return RobustDeviation(
            field_code=field_code,
            robust_z=None,
            median=None,
            mad=None,
            n_observations=len(history),
            reason="insufficient_history",
        )

    centre = median(history)
    absolute_deviation = median([abs(value - centre) for value in history])
    if absolute_deviation == 0.0:
        return RobustDeviation(
            field_code=field_code,
            robust_z=None,
            median=centre,
            mad=0.0,
            n_observations=len(history),
            reason="zero_mad",
        )

    scale = MAD_TO_SIGMA * absolute_deviation
    return RobustDeviation(
        field_code=field_code,
        robust_z=(float(current_value) - centre) / scale,
        median=centre,
        mad=absolute_deviation,
        n_observations=len(history),
    )


def compute_categorical_surprise(
    history: EligibleHistory,
    *,
    current_value: FieldValue | None,
    minimum: int = PERSONAL_MIN_OBSERVATIONS,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> CategoricalSurprise:
    """Dirichlet posterior predictive probability of today's category.

    `other`, a conflict or a thin history leave the rule unavailable rather than
    treating an unusual answer as a surprise it cannot measure.
    """

    field_code = history.stratum.field_code
    support = closed_support(field_code)
    if support is None:
        return CategoricalSurprise(
            field_code=field_code, probability=None, n_observations=0, reason="unsupported_kind"
        )
    if current_value is None:
        return CategoricalSurprise(
            field_code=field_code, probability=None, n_observations=0, reason="no_current_value"
        )
    if current_value == OTHER_VALUE:
        return CategoricalSurprise(
            field_code=field_code, probability=None, n_observations=0, reason="other_category"
        )
    if not history.is_clean:
        return CategoricalSurprise(
            field_code=field_code, probability=None, n_observations=0, reason="conflict"
        )
    if history.n_observations < minimum:
        return CategoricalSurprise(
            field_code=field_code,
            probability=None,
            n_observations=history.n_observations,
            reason="insufficient_history",
        )

    counts = Counter(row.value for row in history.observations)
    alphas = {value: float(prior + counts.get(value, 0)) for value in support}
    total = sum(alphas.values())
    return CategoricalSurprise(
        field_code=field_code,
        probability=alphas[current_value] / total,
        n_observations=history.n_observations,
    )


def detect_form_anomaly(
    answers: Mapping[FieldCode, FieldValue | None],
    *,
    deviations: Sequence[RobustDeviation] = (),
    surprises: Sequence[CategoricalSurprise] = (),
    categorical_cut: float = CATEGORICAL_ANOMALY_PROBABILITY,
    robust_z_cut: float = ROBUST_Z_ANOMALY,
) -> FormAnomaly:
    """Evaluate the six SPEC 6.11 conditions over today's confirmed answers.

    Answering the filter question "no" only stores `relevant_event_flag=false`.
    It never fills in another field and never opens the queue (INV-08).
    """

    triggers: list[FormAnomalyTrigger] = []

    if answers.get(FieldCode.RELEVANT_EVENT_FLAG) is True:
        triggers.append(FormAnomalyTrigger.RELEVANT_EVENT_FLAG)
    if answers.get(FieldCode.MEDICATION_ADHERENCE) == MedicationAdherence.MISSED.value:
        triggers.append(FormAnomalyTrigger.MEDICATION_MISSED)
    if (
        answers.get(FieldCode.DAILY_REGULATION_STATE)
        == DailyRegulationState.FREQUENT_DYSREGULATION.value
    ):
        triggers.append(FormAnomalyTrigger.FREQUENT_DYSREGULATION)
    if answers.get(FieldCode.ALERTNESS) in ALERTNESS_EXTREMES:
        triggers.append(FormAnomalyTrigger.ALERTNESS_EXTREME)

    if any(
        surprise.probability is not None and surprise.probability < categorical_cut
        for surprise in surprises
    ):
        triggers.append(FormAnomalyTrigger.CATEGORICAL_ANOMALY)
    if any(
        deviation.robust_z is not None and abs(deviation.robust_z) >= robust_z_cut
        for deviation in deviations
    ):
        triggers.append(FormAnomalyTrigger.ROBUST_Z_ANOMALY)

    return FormAnomaly(
        opens_queue=bool(triggers),
        triggers=tuple(triggers),
        deviations=tuple(deviations),
        surprises=tuple(surprises),
    )
