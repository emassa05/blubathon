"""Reportes, resoluciones y estado derivado del request (SPEC 4.4, 4.5).

Tres conceptos distintos y ningún estado mutable compartido:

- `OutcomeReport` es lo que una persona declaró (`yes|no|unknown`).
- `OutcomeResolution` es una materialización append-only derivada de la
  proyección vigente al cutoff.
- `OutcomeRequest` es scheduling inmutable; su estado se **deriva** de la
  resolución activa y del reloj, nunca se guarda como segunda máquina.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.contracts.enums import (
    OutcomeReportValue,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    TimingStatus,
)
from apps.api.store.json_columns import dump, load_list
from apps.api.store.projection import project_as_of


def derive_timing_status(
    *, reported_at: str, target_end_at: str, capture_deadline_at: str
) -> TimingStatus:
    """SPEC 4.5. Los límites son exactos y los extremos on_time son inclusivos."""
    if reported_at < target_end_at:
        return TimingStatus.EARLY
    if reported_at <= capture_deadline_at:
        return TimingStatus.ON_TIME
    return TimingStatus.LATE


def create_outcome_request(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    prediction_episode_id: str,
    target_definition_version: str,
    target_start_at: str,
    target_end_at: str,
    capture_deadline_at: str,
    eligible_reporter_roles: tuple[str, ...],
    created_at: str,
) -> str:
    outcome_request_id = str(uuid4())
    connection.execute(
        "INSERT INTO outcome_requests(outcome_request_id, tenant_id, subject_id,"
        " prediction_episode_id, target_definition_version, target_start_at, target_end_at,"
        " capture_deadline_at, eligible_reporter_roles, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            outcome_request_id,
            tenant_id,
            subject_id,
            prediction_episode_id,
            target_definition_version,
            target_start_at,
            target_end_at,
            capture_deadline_at,
            dump(sorted(eligible_reporter_roles)),
            created_at,
        ),
    )
    return outcome_request_id


def outcome_request(
    connection: sqlite3.Connection, prediction_episode_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM outcome_requests WHERE prediction_episode_id = ?",
        (prediction_episode_id,),
    ).fetchone()


@dataclass(frozen=True, slots=True)
class NewReport:
    tenant_id: str
    prediction_episode_id: str
    target_definition_version: str
    reporter_actor_id: str
    reporter_role: str
    value: str
    occurred_at: str | None
    reported_at: str
    timing_status: str
    data_origin: str
    intake_channel: str
    source_mapping_id: str | None
    supersedes_id: str | None
    ingested_at: str


def insert_report(connection: sqlite3.Connection, new: NewReport) -> str:
    outcome_report_id = str(uuid4())
    connection.execute(
        "INSERT INTO outcome_reports(outcome_report_id, tenant_id, prediction_episode_id,"
        " target_definition_version, reporter_actor_id, reporter_role, value, occurred_at,"
        " reported_at, timing_status, data_origin, intake_channel, source_mapping_id,"
        " supersedes_id, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            outcome_report_id,
            new.tenant_id,
            new.prediction_episode_id,
            new.target_definition_version,
            new.reporter_actor_id,
            new.reporter_role,
            new.value,
            new.occurred_at,
            new.reported_at,
            new.timing_status,
            new.data_origin,
            new.intake_channel,
            new.source_mapping_id,
            new.supersedes_id,
            new.ingested_at,
        ),
    )
    return outcome_report_id


def report(connection: sqlite3.Connection, outcome_report_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM outcome_reports WHERE outcome_report_id = ?", (outcome_report_id,)
    ).fetchone()


def active_reports(
    connection: sqlite3.Connection, *, prediction_episode_id: str, cutoff: str
) -> tuple[dict[str, Any], ...]:
    rows = connection.execute(
        "SELECT * FROM outcome_reports WHERE prediction_episode_id = ?",
        (prediction_episode_id,),
    ).fetchall()
    projection = project_as_of((dict(row) for row in rows), cutoff, id_field="outcome_report_id")
    return projection.leaves


def active_resolution(
    connection: sqlite3.Connection, prediction_episode_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM outcome_resolutions WHERE prediction_episode_id = ?"
        " ORDER BY resolution_version DESC LIMIT 1",
        (prediction_episode_id,),
    ).fetchone()


@dataclass(frozen=True, slots=True)
class ResolutionOutcome:
    status: str
    resolved_at: str | None
    qualifying_report_id: str | None
    ever_conflicted: bool


def compute_resolution(
    reports: tuple[dict[str, Any], ...],
    *,
    target_start_at: str,
    target_end_at: str,
    capture_deadline_at: str,
    now: str,
    previously_conflicted: bool,
) -> ResolutionOutcome:
    """SPEC 4.4, algoritmo literal sobre la proyección vigente al cutoff."""

    def in_window(occurred_at: str | None) -> bool:
        # Ventana `(target_start_at, target_end_at]`: extremo inicial abierto.
        return occurred_at is not None and target_start_at < occurred_at <= target_end_at

    eligible_yes = [
        row
        for row in reports
        if row["value"] == OutcomeReportValue.YES.value
        and row["timing_status"] in (TimingStatus.EARLY.value, TimingStatus.ON_TIME.value)
        and in_window(row["occurred_at"])
    ]
    # Un `no` solo es elegible `on_time`: uno temprano queda provisional.
    eligible_no = [
        row
        for row in reports
        if row["value"] == OutcomeReportValue.NO.value
        and row["timing_status"] == TimingStatus.ON_TIME.value
    ]

    def first(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return min(rows, key=lambda row: (row["reported_at"], row["outcome_report_id"]))

    if eligible_yes and eligible_no:
        latest = max(
            (*eligible_yes, *eligible_no),
            key=lambda row: (row["reported_at"], row["outcome_report_id"]),
        )
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.CONFLICTED.value,
            resolved_at=latest["reported_at"],
            qualifying_report_id=None,
            ever_conflicted=True,
        )
    if eligible_yes:
        chosen = first(eligible_yes)
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.YES.value,
            resolved_at=chosen["reported_at"],
            qualifying_report_id=chosen["outcome_report_id"],
            ever_conflicted=previously_conflicted,
        )
    if eligible_no:
        chosen = first(eligible_no)
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.NO.value,
            resolved_at=chosen["reported_at"],
            qualifying_report_id=chosen["outcome_report_id"],
            ever_conflicted=previously_conflicted,
        )
    if now > capture_deadline_at:
        # Sin reporte concluyente al deadline: unknown, nunca `no` (INV-14).
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.UNKNOWN.value,
            resolved_at=capture_deadline_at,
            qualifying_report_id=None,
            ever_conflicted=previously_conflicted,
        )
    return ResolutionOutcome(
        status=OutcomeResolutionStatus.PENDING.value,
        resolved_at=None,
        qualifying_report_id=None,
        ever_conflicted=previously_conflicted,
    )


def materialize_resolution(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    prediction_episode_id: str,
    target_start_at: str,
    target_end_at: str,
    capture_deadline_at: str,
    now: str,
) -> sqlite3.Row:
    """Recalcula y persiste otra versión solo si la resolución cambió.

    `ever_conflicted` es monotónico: un episodio alguna vez conflictivo lo sigue
    siendo aunque una corrección posterior deje un estado limpio.
    """
    active = active_resolution(connection, prediction_episode_id)
    previously_conflicted = bool(active["ever_conflicted"]) if active is not None else False
    reports = active_reports(connection, prediction_episode_id=prediction_episode_id, cutoff=now)
    computed = compute_resolution(
        reports,
        target_start_at=target_start_at,
        target_end_at=target_end_at,
        capture_deadline_at=capture_deadline_at,
        now=now,
        previously_conflicted=previously_conflicted,
    )

    if active is not None and (
        active["status"] == computed.status
        and active["resolved_at"] == computed.resolved_at
        and active["qualifying_report_id"] == computed.qualifying_report_id
        and bool(active["ever_conflicted"]) == computed.ever_conflicted
    ):
        return active

    version = 1 if active is None else int(active["resolution_version"]) + 1
    outcome_resolution_id = str(uuid4())
    connection.execute(
        "INSERT INTO outcome_resolutions(outcome_resolution_id, tenant_id,"
        " prediction_episode_id, status, resolved_at, qualifying_report_id, ever_conflicted,"
        " resolution_version, ingested_at, supersedes_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            outcome_resolution_id,
            tenant_id,
            prediction_episode_id,
            computed.status,
            computed.resolved_at,
            computed.qualifying_report_id,
            int(computed.ever_conflicted),
            version,
            now,
            None if active is None else active["outcome_resolution_id"],
        ),
    )
    refreshed = active_resolution(connection, prediction_episode_id)
    assert refreshed is not None
    return refreshed


def derive_request_status(
    *, resolution_status: str, capture_deadline_at: str, now: str
) -> OutcomeRequestState:
    """SPEC 4.4. El request no guarda estado: se deriva de resolución y reloj."""
    if resolution_status in (OutcomeResolutionStatus.YES.value, OutcomeResolutionStatus.NO.value):
        return OutcomeRequestState.REPORTED
    if resolution_status == OutcomeResolutionStatus.CONFLICTED.value:
        return OutcomeRequestState.CONFLICTED
    if resolution_status == OutcomeResolutionStatus.UNKNOWN.value:
        return OutcomeRequestState.MISSING
    if now > capture_deadline_at:
        return OutcomeRequestState.MISSING
    return OutcomeRequestState.OPEN


def eligible_reporter_roles(row: sqlite3.Row) -> tuple[str, ...]:
    return tuple(load_list(row["eligible_reporter_roles"]))
