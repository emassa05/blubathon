"""Assembling an evaluation report (SPEC 14.3, 14.5).

Every metric names its origin, dataset hash and model, states an interval only
when the bootstrap supported one, and reports `not_estimable` with a reason
rather than a zero. Synthetic reports carry `simulation_only` where a reader
sees it.

Two things are deliberately absent. `alert-budget recall` is always
`not_estimable`, because v0.3 has neither an alert definition nor a decision
policy and adding one would mean versioning both (SPEC 14.3). And no table here
uses the word efficacy: what the recommendation counters describe is exposure
and association, under confounding by indication.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ml.eval.bootstrap import BootstrapInterval, cluster_bootstrap
from ml.eval.metrics import (
    auc_roc,
    average_precision,
    brier_score,
    calibration_fit,
    has_both_classes,
)
from ml.eval.protocol import OutOfFoldResult
from ml.spec_constants import (
    GROUP_METRIC_MIN_NEGATIVES,
    GROUP_METRIC_MIN_POSITIVES,
    GROUP_METRIC_MIN_SUBJECTS,
)
from packages.shared.domain.base import Interval
from packages.shared.domain.evaluation import (
    AbstentionBreakdown,
    DatasetSnapshot,
    EvaluationReport,
    GroupMetric,
    MetricValue,
    SourceMetric,
)
from packages.shared.enums import (
    DataOrigin,
    EvaluationReportStatus,
    IntendedUse,
    MetricStatus,
    Source,
    TrackId,
)

ALERT_BUDGET_RECALL = "alert_budget_recall"

SIMULATION_LIMITATION_ES = (
    "Estas métricas provienen de datos sintéticos (simulation_only). No describen el "
    "rendimiento con personas reales."
)
SELECTION_LIMITATION_ES = (
    "Las tasas se estiman por oportunidad de formulario observada, no como incidencia diaria "
    "poblacional: completar el formulario puede seleccionar los días registrados."
)
DEVELOPMENT_LIMITATION_ES = (
    "Resultados de desarrollo fuera de fold. No habilitan el estado shadow_evaluated, que exige "
    "un periodo prospectivo preregistrado."
)
ASSOCIATION_LIMITATION_ES = (
    "Las asociaciones observadas no son eficacia: hay confusión por indicación y selección "
    "profesional."
)


def estimated(
    name: str,
    value: float,
    *,
    interval: BootstrapInterval | None = None,
    denominator: int | None = None,
) -> MetricValue:
    bounds = None
    if interval is not None and interval.estimable:
        assert interval.lower is not None and interval.upper is not None
        bounds = Interval(
            lower=max(0.0, min(1.0, interval.lower)),
            upper=max(0.0, min(1.0, interval.upper)),
        )
    return MetricValue(
        name=name,
        status=MetricStatus.ESTIMATED,
        value=value,
        interval=bounds,
        denominator=denominator,
    )


def not_estimable(name: str, reason: str, *, denominator: int | None = None) -> MetricValue:
    return MetricValue(
        name=name,
        status=MetricStatus.NOT_ESTIMABLE,
        not_estimable_reason=reason,
        denominator=denominator,
    )


def _bounded_interval(statistic, *, labels, probabilities, subject_ids) -> BootstrapInterval | None:
    if len(labels) < 2:
        return None
    return cluster_bootstrap(
        statistic, labels=labels, probabilities=probabilities, subject_ids=subject_ids
    )


def core_metrics(
    result: OutOfFoldResult, *, with_intervals: bool = True
) -> tuple[MetricValue, ...]:
    """Brier, average precision, AUC, calibration, and the two absent ones."""

    labels = result.labels
    probabilities = result.probabilities
    subject_ids = result.subject_ids
    denominator = len(labels)

    metrics: list[MetricValue] = []

    if not labels:
        metrics.append(not_estimable("brier_score", "no_out_of_fold_predictions"))
        metrics.append(not_estimable("average_precision", "no_out_of_fold_predictions"))
        metrics.append(not_estimable("auc_roc", "no_out_of_fold_predictions"))
        metrics.append(not_estimable("calibration_intercept", "no_out_of_fold_predictions"))
        metrics.append(not_estimable("calibration_slope", "no_out_of_fold_predictions"))
        metrics.append(not_estimable(ALERT_BUDGET_RECALL, "no_decision_policy_version"))
        return tuple(metrics)

    brier = brier_score(labels, probabilities)
    assert brier is not None
    metrics.append(
        estimated(
            "brier_score",
            brier,
            interval=(
                _bounded_interval(
                    brier_score,
                    labels=labels,
                    probabilities=probabilities,
                    subject_ids=subject_ids,
                )
                if with_intervals
                else None
            ),
            denominator=denominator,
        )
    )

    precision = average_precision(labels, probabilities)
    if precision is None:
        metrics.append(not_estimable("average_precision", "single_class", denominator=denominator))
    else:
        metrics.append(
            estimated(
                "average_precision",
                precision,
                interval=(
                    _bounded_interval(
                        average_precision,
                        labels=labels,
                        probabilities=probabilities,
                        subject_ids=subject_ids,
                    )
                    if with_intervals
                    else None
                ),
                denominator=denominator,
            )
        )

    auc = auc_roc(labels, probabilities)
    if auc is None:
        metrics.append(not_estimable("auc_roc", "single_class", denominator=denominator))
    else:
        metrics.append(estimated("auc_roc", auc, denominator=denominator))

    calibration = calibration_fit(labels, probabilities)
    if calibration.estimable:
        assert calibration.intercept is not None and calibration.slope is not None
        metrics.append(
            MetricValue(
                name="calibration_intercept",
                status=MetricStatus.ESTIMATED,
                value=calibration.intercept,
                denominator=denominator,
            )
        )
        metrics.append(
            MetricValue(
                name="calibration_slope",
                status=MetricStatus.ESTIMATED,
                value=calibration.slope,
                denominator=denominator,
            )
        )
    else:
        reason = calibration.not_estimable_reason or "not_estimable"
        metrics.append(not_estimable("calibration_intercept", reason, denominator=denominator))
        metrics.append(not_estimable("calibration_slope", reason, denominator=denominator))

    # SPEC 14.3: no alert definition and no decision policy exist in v0.3.
    metrics.append(not_estimable(ALERT_BUDGET_RECALL, "no_decision_policy_version"))
    return tuple(metrics)


def completeness_metrics(result: OutOfFoldResult) -> tuple[MetricValue, ...]:
    """Counts and completeness, the only honest output with a single class."""

    labels = result.labels
    positives = sum(labels)
    return (
        MetricValue(
            name="labelled_episodes",
            status=MetricStatus.ESTIMATED,
            value=float(len(labels)),
            denominator=len(result.predictions),
        ),
        MetricValue(
            name="positive_outcomes",
            status=MetricStatus.ESTIMATED,
            value=float(positives),
            denominator=len(labels),
        ),
        MetricValue(
            name="negative_outcomes",
            status=MetricStatus.ESTIMATED,
            value=float(len(labels) - positives),
            denominator=len(labels),
        ),
    )


def decision_coverage(result: OutOfFoldResult) -> MetricValue:
    """`outputs status=ok / eligible primary episodes` (SPEC 14.4)."""

    if not result.predictions:
        return not_estimable("decision_coverage", "no_eligible_episodes")
    return MetricValue(
        name="decision_coverage",
        status=MetricStatus.ESTIMATED,
        value=result.coverage,
        denominator=len(result.predictions),
    )


def abstention_breakdown(result: OutOfFoldResult) -> tuple[AbstentionBreakdown, ...]:
    """Every abstention reason over the same denominator as coverage."""

    total = len(result.predictions)
    if not total:
        return ()
    counts = result.abstention_counts()
    return tuple(
        AbstentionBreakdown(reason=reason, count=count, rate=count / total)
        for reason, count in sorted(counts.items())
    )


@dataclass(frozen=True, slots=True)
class GroupRows:
    """One group and the out-of-fold rows that belong to it."""

    group_kind: str
    group_value: str
    subject_ids: tuple[UUID, ...]
    labels: tuple[int, ...]
    probabilities: tuple[float, ...]


def group_metrics(groups: Iterable[GroupRows]) -> tuple[GroupMetric, ...]:
    """Suppress a group below the privacy minimums, counts included (SPEC 14.4)."""

    reported: list[GroupMetric] = []
    for group in groups:
        subjects = len(set(group.subject_ids))
        positives = sum(group.labels)
        negatives = len(group.labels) - positives
        suppressed = (
            subjects < GROUP_METRIC_MIN_SUBJECTS
            or positives < GROUP_METRIC_MIN_POSITIVES
            or negatives < GROUP_METRIC_MIN_NEGATIVES
        )
        if suppressed:
            # Small counts are not shown indirectly either, so the counts are
            # reported as zero rather than as a number a reader could difference.
            reported.append(
                GroupMetric(
                    group_kind=group.group_kind,
                    group_value=group.group_value,
                    subject_count=0,
                    positive_count=0,
                    negative_count=0,
                    suppressed=True,
                    metrics=(),
                )
            )
            continue
        brier = brier_score(group.labels, group.probabilities)
        precision = average_precision(group.labels, group.probabilities)
        metrics: list[MetricValue] = []
        if brier is not None:
            metrics.append(estimated("brier_score", brier, denominator=len(group.labels)))
        if precision is None:
            metrics.append(
                not_estimable("average_precision", "single_class", denominator=len(group.labels))
            )
        else:
            metrics.append(estimated("average_precision", precision, denominator=len(group.labels)))
        reported.append(
            GroupMetric(
                group_kind=group.group_kind,
                group_value=group.group_value,
                subject_count=subjects,
                positive_count=positives,
                negative_count=negatives,
                suppressed=False,
                metrics=tuple(metrics),
            )
        )
    return tuple(reported)


def source_metrics(
    rows_by_source: Mapping[Source, tuple[Sequence[int], Sequence[float]]],
) -> tuple[SourceMetric, ...]:
    """Metrics per observation context, in canonical source order."""

    reported: list[SourceMetric] = []
    for source in Source:
        rows = rows_by_source.get(source)
        if rows is None:
            continue
        labels, probabilities = rows
        brier = brier_score(labels, probabilities)
        metrics: list[MetricValue] = []
        if brier is None:
            metrics.append(not_estimable("brier_score", "no_rows"))
        else:
            metrics.append(estimated("brier_score", brier, denominator=len(labels)))
        precision = average_precision(labels, probabilities)
        if precision is None:
            metrics.append(
                not_estimable("average_precision", "single_class", denominator=len(labels))
            )
        else:
            metrics.append(estimated("average_precision", precision, denominator=len(labels)))
        reported.append(SourceMetric(source=source, metrics=tuple(metrics)))
    return tuple(reported)


def limitations(*, data_origin: DataOrigin) -> tuple[str, ...]:
    """The limitations every report has to carry, in Spanish (SPEC 14.3)."""

    lines = [SELECTION_LIMITATION_ES, DEVELOPMENT_LIMITATION_ES, ASSOCIATION_LIMITATION_ES]
    if data_origin is DataOrigin.SYNTHETIC:
        lines.insert(0, SIMULATION_LIMITATION_ES)
    return tuple(lines)


def build_evaluation_report(
    result: OutOfFoldResult,
    *,
    evaluation_report_id: UUID,
    snapshot: DatasetSnapshot,
    model_version: str,
    track_id: TrackId,
    intended_use: IntendedUse,
    protocol_version: str,
    created_at: datetime,
    groups: Iterable[GroupRows] = (),
    rows_by_source: Mapping[Source, tuple[Sequence[int], Sequence[float]]] | None = None,
    with_intervals: bool = True,
) -> EvaluationReport:
    """One report, one exact target definition version, everything declared."""

    if snapshot.data_origin is DataOrigin.SYNTHETIC and intended_use is not (
        IntendedUse.SIMULATION_ONLY
    ):
        raise ValueError("a synthetic report is simulation_only and says so (INV-34)")

    metrics = (
        core_metrics(result, with_intervals=with_intervals)
        if has_both_classes(result.labels)
        else (*core_metrics(result, with_intervals=with_intervals), *completeness_metrics(result))
    )
    return EvaluationReport(
        evaluation_report_id=evaluation_report_id,
        tenant_id=snapshot.tenant_id,
        model_version=model_version,
        track_id=track_id,
        dataset_snapshot_id=snapshot.dataset_snapshot_id,
        dataset_sha256=snapshot.content_sha256,
        data_origin=snapshot.data_origin,
        intended_use=intended_use,
        target_definition_version=snapshot.target_definition_version,
        protocol_version=protocol_version,
        status=EvaluationReportStatus.DRAFT,
        metrics=metrics,
        group_metrics=group_metrics(groups),
        source_metrics=source_metrics(rows_by_source or {}),
        decision_coverage=decision_coverage(result),
        abstentions=abstention_breakdown(result),
        limitations_es=limitations(data_origin=snapshot.data_origin),
        created_at=created_at,
        detail={
            "selected_penalties": {
                str(subject_id): penalty for subject_id, penalty in result.selected_penalties
            },
            "out_of_fold_rows": len(result.estimated),
            "eligible_episodes": len(result.predictions),
        },
    )
