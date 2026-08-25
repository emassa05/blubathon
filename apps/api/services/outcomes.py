"""Servicio de outcomes (SPEC 4.4, 4.5, 11.4).

El servidor toma actor, rol, tenant, `reported_at`, target y definición desde el
contexto autorizado. El cliente solo envía `value` y, para `yes`, `occurred_at`.
"""

from __future__ import annotations

import sqlite3

from apps.api.auth.context import ActorContext
from apps.api.canonical import canonical_timestamp
from apps.api.contracts.enums import (
    CohortKind,
    DataOrigin,
    GrantCapability,
    IntakeChannel,
    OutcomeReportValue,
    OutcomeResolutionStatus,
)
from apps.api.contracts.models import (
    OutcomeReportRequest,
    OutcomeReportResponseView,
    OutcomeReportView,
    OutcomeRequestListResponse,
    OutcomeRequestView,
    OutcomeResolutionView,
)
from apps.api.errors import AuditIntent, forbidden, invalid, not_found
from apps.api.services.base import Services
from apps.api.store import audit, episodes, identity
from apps.api.store import outcomes as outcomes_store
from apps.api.store.json_columns import load_list


class OutcomeService:
    def __init__(self, services: Services) -> None:
        self._services = services

    # -- inbox -----------------------------------------------------------

    def list_requests(
        self, connection: sqlite3.Connection, *, actor: ActorContext, now: str
    ) -> OutcomeRequestListResponse:
        """SPEC 4.4: resolución pending, deadline abierto, rol y grant activos.

        El filtro por sujeto ocurre en SQL con los grants del actor; no se cargan
        filas prohibidas para descartarlas después.
        """
        subject_ids = self._services.authorization.granted_subject_ids(
            connection,
            actor=actor,
            capability=GrantCapability.OUTCOME_REPORT,
            cutoff=now,
        )
        if not subject_ids:
            return OutcomeRequestListResponse(items=[])
        placeholders = ",".join("?" for _ in subject_ids)
        rows = connection.execute(
            "SELECT r.*, s.display_label FROM outcome_requests AS r"
            " JOIN subjects AS s ON s.subject_id = r.subject_id"
            f" WHERE r.tenant_id = ? AND r.subject_id IN ({placeholders})"
            " AND r.capture_deadline_at >= ?"
            " ORDER BY r.capture_deadline_at",
            (actor.tenant_id, *subject_ids, now),
        ).fetchall()

        items: list[OutcomeRequestView] = []
        for row in rows:
            roles = outcomes_store.eligible_reporter_roles(row)
            if not any(actor.has_role(role) for role in roles):
                continue
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
                    severity_anchors_es=[
                        str(item) for item in load_list(target_row["severity_anchors_es"])
                    ],
                    target_start_at=row["target_start_at"],
                    target_end_at=row["target_end_at"],
                    capture_deadline_at=row["capture_deadline_at"],
                    state=state.value,
                    resolution_status=resolution["status"],
                )
            )
        return OutcomeRequestListResponse(items=items)

    # -- reautorización de replay -----------------------------------------

    def authorize_report(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        prediction_episode_id: str,
        now: str,
    ) -> None:
        episode = episodes.episode(connection, prediction_episode_id)
        if episode is None or episode["tenant_id"] != actor.tenant_id:
            raise not_found()
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=episode["subject_id"],
            capability=GrantCapability.OUTCOME_REPORT,
            cutoff=now,
            action="outcome_report_replay",
        )
        request_row = outcomes_store.outcome_request(connection, prediction_episode_id)
        if request_row is None:
            raise not_found()
        if not any(
            actor.has_role(role) for role in outcomes_store.eligible_reporter_roles(request_row)
        ):
            raise forbidden("role_not_allowed")

    # -- reporte ---------------------------------------------------------

    def create_report(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        prediction_episode_id: str,
        request: OutcomeReportRequest,
        now: str,
    ) -> OutcomeReportResponseView:
        episode = episodes.episode(connection, prediction_episode_id)
        if episode is None or episode["tenant_id"] != actor.tenant_id:
            raise not_found()
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=episode["subject_id"],
            capability=GrantCapability.OUTCOME_REPORT,
            cutoff=now,
            action="outcome_report",
        )
        request_row = outcomes_store.outcome_request(connection, prediction_episode_id)
        if request_row is None:
            raise not_found()

        eligible_roles = outcomes_store.eligible_reporter_roles(request_row)
        reporter_role = next((role for role in eligible_roles if actor.has_role(role)), None)
        if reporter_role is None:
            # SPEC 11.4: el rol debe estar permitido por la definición del target.
            raise forbidden(
                "role_not_allowed",
                audit=AuditIntent(
                    action="outcome_report",
                    resource_type="outcome_request",
                    decision="denied",
                    reason_code="role_not_allowed",
                    tenant_id=actor.tenant_id,
                    actor_id=actor.actor_id,
                    resource_id=request_row["outcome_request_id"],
                    subject_id=episode["subject_id"],
                    request_id=actor.request_id,
                ),
            )

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
                (supersedes_id, actor.tenant_id, prediction_episode_id),
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
                tenant_id=actor.tenant_id,
                prediction_episode_id=prediction_episode_id,
                target_definition_version=episode["target_definition_version"],
                reporter_actor_id=actor.actor_id,
                reporter_role=reporter_role,
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
            tenant_id=actor.tenant_id,
            prediction_episode_id=prediction_episode_id,
            target_start_at=episode["target_start_at"],
            target_end_at=episode["target_end_at"],
            capture_deadline_at=episode["capture_deadline_at"],
            now=now,
        )
        audit.record(
            connection,
            actor=actor,
            action="outcome_report",
            resource_type="outcome_report",
            resource_id=outcome_report_id,
            subject_id=episode["subject_id"],
            decision="allowed",
            reason_code=timing_status.value,
            occurred_at=now,
            request_id=actor.request_id,
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

    # -- soporte ---------------------------------------------------------

    def _refresh_resolution(
        self, connection: sqlite3.Connection, *, row: sqlite3.Row, now: str
    ) -> sqlite3.Row:
        """SPEC 4.4: al pasar el deadline se materializa `unknown` antes de derivar."""
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
