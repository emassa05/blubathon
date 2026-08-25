"""Evaluate one training run under a versioned protocol (TAREAS P1.9).

The run and the evaluation are separate artifacts on purpose: a run says whether
a model could be fitted, an evaluation says what it does out of fold. Both are
written as manifests P2 imports; neither trains or evaluates inside the API, and
neither promotes anything.

A report covers exactly one `target_definition_version`, the one its snapshot
carries. v0.3 defines no way to pool different questions or anchors, so two
versions produce two datasets and two reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from ml.eval.protocol import OutOfFoldResult, evaluation_protocol, nested_out_of_fold
from ml.eval.report import GroupRows, build_evaluation_report
from packages.shared.domain.evaluation import EvaluationProtocolVersion, EvaluationReport
from packages.shared.enums import DataOrigin, IntendedUse, Source
from tools.train.run import TrainingOutcome


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    """The report, the protocol that produced it and the raw out-of-fold rows."""

    report: EvaluationReport
    protocol: EvaluationProtocolVersion
    out_of_fold: OutOfFoldResult


def evaluate_run(
    outcome: TrainingOutcome,
    *,
    evaluation_report_id: UUID,
    created_at: datetime,
    source: Source = Source.HOME,
    groups: tuple[GroupRows, ...] = (),
    with_intervals: bool = True,
) -> EvaluationOutcome:
    """Nested out-of-fold evaluation over the landmarks the run built."""

    protocol = evaluation_protocol(outcome.reveal_events)
    result = nested_out_of_fold(outcome.landmarks)
    intended_use = (
        IntendedUse.SIMULATION_ONLY
        if outcome.snapshot.data_origin is DataOrigin.SYNTHETIC
        else IntendedUse.SHADOW_EVALUATION
    )
    report = build_evaluation_report(
        result,
        evaluation_report_id=evaluation_report_id,
        snapshot=outcome.snapshot,
        model_version=outcome.run.model_version or outcome.protocol.protocol_version,
        track_id=outcome.run.track_id,
        intended_use=intended_use,
        protocol_version=protocol.protocol_version,
        created_at=created_at,
        groups=groups,
        rows_by_source={source: (result.labels, result.probabilities)},
        with_intervals=with_intervals,
    )
    return EvaluationOutcome(report=report, protocol=protocol, out_of_fold=result)


def evaluation_report_payload(outcome: EvaluationOutcome) -> dict[str, Any]:
    """A non-identifiable manifest: versions, hashes, counts and metrics."""

    report = outcome.report
    return {
        "evaluation_report_id": str(report.evaluation_report_id),
        "status": report.status.value,
        "model_version": report.model_version,
        "track_id": report.track_id.value,
        "data_origin": report.data_origin.value,
        "intended_use": report.intended_use.value,
        "simulation_only": report.is_simulation_only,
        "target_definition_version": report.target_definition_version,
        "dataset_snapshot_id": str(report.dataset_snapshot_id),
        "dataset_sha256": report.dataset_sha256,
        "protocol_version": report.protocol_version,
        "protocol_sha256": outcome.protocol.content_sha256,
        "reveal_schedule_sha256": outcome.protocol.reveal_schedule_sha256,
        "metrics": [metric.model_dump(mode="json") for metric in report.metrics],
        "group_metrics": [metric.model_dump(mode="json") for metric in report.group_metrics],
        "source_metrics": [metric.model_dump(mode="json") for metric in report.source_metrics],
        "decision_coverage": (
            report.decision_coverage.model_dump(mode="json")
            if report.decision_coverage is not None
            else None
        ),
        "abstentions": [item.model_dump(mode="json") for item in report.abstentions],
        "limitations_es": list(report.limitations_es),
        "detail": report.detail,
    }
