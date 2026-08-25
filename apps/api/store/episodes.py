"""Episodios primarios, snapshots y outputs por track (SPEC 4.1-4.2, 8, 11.5)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.canonical import domain_hash
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.contracts.enums import EpisodeRole, EpisodeStatus
from apps.api.errors import conflict
from apps.api.ports.prediction import TrackOutput
from apps.api.store.json_columns import dump, load_list


@dataclass(frozen=True, slots=True)
class NewEpisode:
    tenant_id: str
    subject_id: str
    form_session_id: str
    as_of_at: str
    target_start_at: str
    target_end_at: str
    capture_deadline_at: str
    target_definition_version: str
    profile_version: str | None
    care_mode: str | None
    input_data_origin: str
    created_at: str


def create_primary_episode(connection: sqlite3.Connection, new: NewEpisode) -> str:
    """SPEC 4.2. La transacción llamante ya serializó por (tenant, subject).

    Se vuelve a comprobar el solape dentro de la transacción: si otra sesión
    ganó la carrera, la operación falla cerrado en vez de crear una ventana
    solapada.
    """
    overlapping = connection.execute(
        "SELECT prediction_episode_id FROM prediction_episodes"
        " WHERE tenant_id = ? AND subject_id = ? AND role = 'primary'"
        " AND target_end_at > ? AND target_start_at <= ?",
        (new.tenant_id, new.subject_id, new.as_of_at, new.as_of_at),
    ).fetchone()
    if overlapping is not None:
        raise conflict("revision_conflict", prediction_episode_id=overlapping[0])

    prediction_episode_id = str(uuid4())
    connection.execute(
        "INSERT INTO prediction_episodes(prediction_episode_id, tenant_id, subject_id,"
        " form_session_id, role, status, as_of_at, prediction_at, target_start_at,"
        " target_end_at, capture_deadline_at, target_definition_version, profile_version,"
        " care_mode, input_data_origin, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            prediction_episode_id,
            new.tenant_id,
            new.subject_id,
            new.form_session_id,
            EpisodeRole.PRIMARY.value,
            EpisodeStatus.COMPLETED.value,
            new.as_of_at,
            new.as_of_at,
            new.target_start_at,
            new.target_end_at,
            new.capture_deadline_at,
            new.target_definition_version,
            new.profile_version,
            new.care_mode,
            new.input_data_origin,
            new.created_at,
        ),
    )
    return prediction_episode_id


def episode(connection: sqlite3.Connection, prediction_episode_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM prediction_episodes WHERE prediction_episode_id = ?",
        (prediction_episode_id,),
    ).fetchone()


def create_feature_snapshot(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    prediction_episode_id: str,
    as_of_at: str,
    input_data_origin: str,
    projected_observation_ids: tuple[str, ...],
    projected_outcome_ids: tuple[str, ...],
    consent_ids: tuple[str, ...],
    profile_version: str | None,
    care_mode: str | None,
    created_at: str,
) -> str:
    """SPEC 5.8: persiste los IDs exactos proyectados y su hash. No se recalcula."""
    payload = {
        "as_of_at": as_of_at,
        "input_data_origin": input_data_origin,
        "projected_observation_ids": sorted(projected_observation_ids),
        "projected_outcome_ids": sorted(projected_outcome_ids),
        "consent_ids": sorted(consent_ids),
        "profile_version": profile_version,
        "care_mode": care_mode,
    }
    feature_snapshot_id = str(uuid4())
    connection.execute(
        "INSERT INTO feature_snapshots(feature_snapshot_id, tenant_id, prediction_episode_id,"
        " as_of_at, input_data_origin, projected_observation_ids, projected_outcome_ids,"
        " consent_ids, profile_version, care_mode, content_sha256, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            feature_snapshot_id,
            tenant_id,
            prediction_episode_id,
            as_of_at,
            input_data_origin,
            dump(sorted(projected_observation_ids)),
            dump(sorted(projected_outcome_ids)),
            dump(sorted(consent_ids)),
            profile_version,
            care_mode,
            domain_hash("feature_snapshot", SPEC_VERSION, payload),
            created_at,
        ),
    )
    return feature_snapshot_id


def snapshot(connection: sqlite3.Connection, prediction_episode_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM feature_snapshots WHERE prediction_episode_id = ?",
        (prediction_episode_id,),
    ).fetchone()


def insert_prediction_output(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    prediction_episode_id: str,
    output: TrackOutput,
    created_at: str,
) -> str:
    prediction_output_id = str(uuid4())
    interval_low, interval_high = output.interval or (None, None)
    connection.execute(
        "INSERT INTO prediction_outputs(prediction_output_id, tenant_id,"
        " prediction_episode_id, track_id, intended_use, status, estimate_kind, probability,"
        " simulation_score, interval_low, interval_high, interval_method,"
        " abstention_reasons, model_version, input_data_origin, exposed, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            prediction_output_id,
            tenant_id,
            prediction_episode_id,
            output.track_id,
            output.intended_use,
            output.status,
            output.estimate_kind,
            output.probability,
            output.simulation_score,
            interval_low,
            interval_high,
            output.interval_method,
            dump(list(output.abstention_reasons)),
            output.model_version,
            output.input_data_origin,
            int(output.exposed),
            created_at,
        ),
    )
    return prediction_output_id


def exposed_outputs(
    connection: sqlite3.Connection, prediction_episode_id: str
) -> list[dict[str, Any]]:
    """SPEC 8.5: el challenger en sombra no sale de la base."""
    rows = connection.execute(
        "SELECT * FROM prediction_outputs WHERE prediction_episode_id = ? AND exposed = 1"
        " ORDER BY track_id",
        (prediction_episode_id,),
    ).fetchall()
    return [
        dict(row) | {"abstention_reasons": load_list(row["abstention_reasons"])} for row in rows
    ]
