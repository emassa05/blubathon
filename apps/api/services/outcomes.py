"""Outcome inbox and reporting for the fixed tenant."""

from __future__ import annotations

import sqlite3

from apps.api.canonical import canonical_timestamp
from apps.api.contracts.enums import (
    CohortKind,
    DataOrigin,
    IntakeChannel,
    OutcomeReportValue,
    OutcomeResolutionStatus,
    Role,
)
from apps.api.contracts.models import (
    OutcomeReportRequest,
    OutcomeReportResponseView,
    OutcomeReportView,
    OutcomeRequestListResponse,
    OutcomeRequestView,
    OutcomeResolutionView,
)
from apps.api.errors import invalid, not_found
from apps.api.services.base import Services
from apps.api.store import episodes, identity
from apps.api.store import outcomes as outcomes_store
from apps.api.store.json_columns import load_list
from tools.seed import ids


class OutcomeService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def list_requests(
        self, connection: sqlite3.Connection, *, tenant_id: str, now: str
    ) -> OutcomeRequestListResponse:
        rows = connection.execute(
            "SELECT r.* FROM outcome_requests AS r"
            " WHERE r.tenant_id = ? AND r.capture_deadline_at >= ?"
            " ORDER BY r.capture_deadline_at",
            (tenant_id, now),
        ).fetchall()
        items = []
        for row in rows:
            resolution = self._refresh_resolution(connection, row=row, now=now)
            if resolution["status"] != OutcomeResolutionStatus.PENDING.value:
                continue
            target_row = identity.target_definition(connection, row["target_definition_version"])
            if target_row is None:
                continue
            state = outcomes_store.derive_request_status(
                resolution_status=resolution["status"],
                capture_deadline_at=row["capture_deadline_at"],
                now=now,
            )
            items.append(
                OutcomeRequestView(
                    outcome_request_id=row["outcome_request_id"],
                    prediction_episode_id=row["prediction_episode_id"],
                    subject_id=row["subject_id"],
                    target_definition_version=row["target_definition_version"],
                    question_es=target_row["question_es"],
                    severity_anchors_es=tuple(
                        str(item) for item in load_list(target_row["severity_anchors_es"])
                    ),
                    target_start_at=row["target_start_at"],
                    target_end_at=row["target_end_at"],
                    capture_deadline_at=row["capture_deadline_at"],
                    state=state.value,
                    resolution_status=resolution["status"],
                )
            )
        return OutcomeRequestListResponse(items=items)

    def create_report(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        prediction_episode_id: str,
        request: OutcomeReportRequest,
        now: str,
    ) -> OutcomeReportResponseView:
        episode = episodes.episode(connection, prediction_episode_id)
        if episode is None or episode["tenant_id"] != tenant_id:
            raise not_found()
        if outcomes_store.outcome_request(connection, prediction_episode_id) is None:
            raise not_found()

        value = OutcomeReportValue(request.value)
        occurred_at = (
            None if request.occurred_at is None else canonical_timestamp(request.occurred_at)
        )
        if value is OutcomeReportValue.YES:
            if occurred_at is None:
                raise invalid("outcome_occurred_at_required")
            if not (episode["target_start_at"] < occurred_at <= episode["target_end_at"]):
                raise invalid("outcome_report_invalid_timing")
            if occurred_at > now:
                raise invalid("outcome_report_invalid_timing")
        elif occurred_at is not None:
            raise invalid("outcome_occurred_at_forbidden")

        supersedes_id = None if request.supersedes_id is None else str(request.supersedes_id)
        if supersedes_id is not None:
            previous = connection.execute(
                "SELECT outcome_report_id FROM outcome_reports WHERE outcome_report_id = ?"
                " AND tenant_id = ? AND prediction_episode_id = ?",
                (supersedes_id, tenant_id, prediction_episode_id),
            ).fetchone()
            if previous is None:
                raise invalid("validation_error", reason="supersedes_id_not_correctable")

        timing_status = outcomes_store.derive_timing_status(
            reported_at=now,
            target_end_at=episode["target_end_at"],
            capture_deadline_at=episode["capture_deadline_at"],
        )
        subject = identity.subject(connection, episode["subject_id"])
        assert subject is not None
        origin = (
            DataOrigin.SYNTHETIC
            if subject["cohort_kind"] == CohortKind.DEMO_FIXTURE.value
            else DataOrigin.REAL
        )
        outcome_report_id = outcomes_store.insert_report(
            connection,
            outcomes_store.NewReport(
                tenant_id=tenant_id,
                prediction_episode_id=prediction_episode_id,
                target_definition_version=episode["target_definition_version"],
                reporter_actor_id=str(ids.CAREGIVER_A),
                reporter_role=Role.CAREGIVER.value,
                value=value.value,
                occurred_at=occurred_at,
                reported_at=now,
                timing_status=timing_status.value,
                data_origin=origin.value,
                intake_channel=IntakeChannel.FORM.value,
                source_mapping_id=None,
                supersedes_id=supersedes_id,
                ingested_at=now,
            ),
        )
        resolution = outcomes_store.materialize_resolution(
            connection,
            tenant_id=tenant_id,
            prediction_episode_id=prediction_episode_id,
            target_start_at=episode["target_start_at"],
            target_end_at=episode["target_end_at"],
            capture_deadline_at=episode["capture_deadline_at"],
            now=now,
        )
        report_row = outcomes_store.report(connection, outcome_report_id)
        assert report_row is not None
        state = outcomes_store.derive_request_status(
            resolution_status=resolution["status"],
            capture_deadline_at=episode["capture_deadline_at"],
            now=now,
        )
        return OutcomeReportResponseView(
            report=_report_view(report_row),
            resolution=_resolution_view(resolution),
            request_state=state.value,
        )

    def _refresh_resolution(
        self, connection: sqlite3.Connection, *, row: sqlite3.Row, now: str
    ) -> sqlite3.Row:
        return outcomes_store.materialize_resolution(
            connection,
            tenant_id=row["tenant_id"],
            prediction_episode_id=row["prediction_episode_id"],
            target_start_at=row["target_start_at"],
            target_end_at=row["target_end_at"],
            capture_deadline_at=row["capture_deadline_at"],
            now=now,
        )


def _report_view(row: sqlite3.Row) -> OutcomeReportView:
    return OutcomeReportView(
        outcome_report_id=row["outcome_report_id"],
        prediction_episode_id=row["prediction_episode_id"],
        value=row["value"],
        occurred_at=row["occurred_at"],
        reported_at=row["reported_at"],
        timing_status=row["timing_status"],
        reporter_role=row["reporter_role"],
        intake_channel=row["intake_channel"],
        target_definition_version=row["target_definition_version"],
    )


def _resolution_view(row: sqlite3.Row) -> OutcomeResolutionView:
    return OutcomeResolutionView(
        status=row["status"],
        resolved_at=row["resolved_at"],
        qualifying_report_id=row["qualifying_report_id"],
        ever_conflicted=bool(row["ever_conflicted"]),
        resolution_version=int(row["resolution_version"]),
    )


resolution_view = _resolution_view
