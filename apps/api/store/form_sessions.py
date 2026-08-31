"""Comandos de sesión de formulario, presentaciones y observaciones.

Todo es append-only: una
corrección de observación crea otra fila con `supersedes_id`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.contracts.enums import FormSessionStatus
from apps.api.store.json_columns import dump, load
from apps.api.store.projection import project_as_of


@dataclass(frozen=True, slots=True)
class NewSession:
    tenant_id: str
    subject_id: str
    actor_id: str
    source: str
    session_kind: str
    audit_mode: bool
    audit_bucket: int
    form_policy_version: str
    local_date: str
    opened_at: str


def create_submission(connection: sqlite3.Connection, new: NewSession) -> str:
    form_session_id = str(uuid4())
    connection.execute(
        "INSERT INTO form_sessions(form_session_id, tenant_id, subject_id, actor_id,"
        " source, session_kind, status, audit_mode, audit_bucket, form_policy_version,"
        " local_date, opened_at, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            form_session_id,
            new.tenant_id,
            new.subject_id,
            new.actor_id,
            new.source,
            new.session_kind,
            FormSessionStatus.SUBMITTED.value,
            int(new.audit_mode),
            new.audit_bucket,
            new.form_policy_version,
            new.local_date,
            new.opened_at,
            new.opened_at,
        ),
    )
    return form_session_id


def session(connection: sqlite3.Connection, form_session_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM form_sessions WHERE form_session_id = ?", (form_session_id,)
    ).fetchone()


def open_primary_episode(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    at: str,
) -> sqlite3.Row | None:
    """Episodio primario cuya ventana sigue abierta en `at`."""
    return connection.execute(
        "SELECT * FROM prediction_episodes"
        " WHERE tenant_id = ? AND subject_id = ? AND role = 'primary'"
        " AND target_end_at > ?"
        " ORDER BY target_start_at DESC LIMIT 1",
        (tenant_id, subject_id, at),
    ).fetchone()


def set_submission_result(
    connection: sqlite3.Connection,
    *,
    form_session_id: str,
    submitted_at: str,
    prediction_status: str,
    prediction_episode_id: str | None,
    linked_prediction_episode_id: str | None,
) -> None:
    """Una sesión siempre puede cerrar y persistir observaciones."""
    connection.execute(
        "UPDATE form_sessions SET status = ?, submitted_at = ?, prediction_status = ?,"
        " prediction_episode_id = ?, linked_prediction_episode_id = ?"
        " WHERE form_session_id = ?",
        (
            FormSessionStatus.SUBMITTED.value,
            submitted_at,
            prediction_status,
            prediction_episode_id,
            linked_prediction_episode_id,
            form_session_id,
        ),
    )


# -- presentaciones ------------------------------------------------------


def record_default_presentation(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    form_session_id: str,
    field_code: str,
    value: Any,
    candidate_count: int,
    posterior_mean: float,
    lower_bound: float,
    n_observations: int,
    estimator_version: str,
    presented_at: str,
) -> str:
    default_presentation_id = str(uuid4())
    connection.execute(
        "INSERT INTO default_presentations(default_presentation_id, tenant_id, subject_id,"
        " form_session_id, field_code, candidate_value, candidate_count, posterior_mean,"
        " lower_bound, n_observations, estimator_version, presented_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            default_presentation_id,
            tenant_id,
            subject_id,
            form_session_id,
            field_code,
            dump(value),
            candidate_count,
            posterior_mean,
            lower_bound,
            n_observations,
            estimator_version,
            presented_at,
        ),
    )
    return default_presentation_id


def current_default_presentation(
    connection: sqlite3.Connection, *, form_session_id: str, field_code: str
) -> sqlite3.Row | None:
    """Presentación vigente: la última no superseded de esa sesión y campo."""
    return connection.execute(
        "SELECT * FROM default_presentations"
        " WHERE form_session_id = ? AND field_code = ? AND superseded_at IS NULL"
        " ORDER BY presented_at DESC LIMIT 1",
        (form_session_id, field_code),
    ).fetchone()


def session_default_presentations(
    connection: sqlite3.Connection, form_session_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM default_presentations WHERE form_session_id = ?"
        " AND superseded_at IS NULL ORDER BY field_code",
        (form_session_id,),
    ).fetchall()


# -- observaciones -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NewObservation:
    tenant_id: str
    subject_id: str
    form_session_id: str | None
    field_code: str
    value: Any | None
    source: str
    actor_id: str
    entry_mode: str
    data_origin: str
    cohort_kind: str
    effective_at: str
    ingested_at: str
    local_date: str
    source_mapping_id: str | None = None
    default_presentation_id: str | None = None
    supersedes_id: str | None = None


def insert_observation(connection: sqlite3.Connection, new: NewObservation) -> str:
    field_observation_id = str(uuid4())
    connection.execute(
        "INSERT INTO field_observations(field_observation_id, tenant_id, subject_id,"
        " form_session_id, field_code, value, source, actor_id, entry_mode, data_origin,"
        " cohort_kind, effective_at, ingested_at, local_date, source_mapping_id,"
        " default_presentation_id, supersedes_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            field_observation_id,
            new.tenant_id,
            new.subject_id,
            new.form_session_id,
            new.field_code,
            None if new.value is None else dump(new.value),
            new.source,
            new.actor_id,
            new.entry_mode,
            new.data_origin,
            new.cohort_kind,
            new.effective_at,
            new.ingested_at,
            new.local_date,
            new.source_mapping_id,
            new.default_presentation_id,
            new.supersedes_id,
        ),
    )
    return field_observation_id


def session_observations(
    connection: sqlite3.Connection, form_session_id: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM field_observations WHERE form_session_id = ?"
        " ORDER BY ingested_at, field_observation_id",
        (form_session_id,),
    ).fetchall()
    return [dict(row) | {"value": load(row["value"])} for row in rows]


def answered_field_codes(connection: sqlite3.Connection, form_session_id: str) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT DISTINCT field_code FROM field_observations WHERE form_session_id = ?",
        (form_session_id,),
    ).fetchall()
    return tuple(row["field_code"] for row in rows)


def projected_session_observations(
    connection: sqlite3.Connection, *, form_session_id: str, cutoff: str
) -> tuple[dict[str, Any], ...]:
    """Hojas vigentes de esta sesión al cutoff."""
    rows = connection.execute(
        "SELECT * FROM field_observations WHERE form_session_id = ?",
        (form_session_id,),
    ).fetchall()
    projection = project_as_of(
        (dict(row) for row in rows),
        cutoff,
        id_field="field_observation_id",
        effective_field="effective_at",
    )
    return tuple(dict(row) | {"value": load(row["value"])} for row in projection.leaves)
