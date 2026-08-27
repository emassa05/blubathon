"""Traducción de filas SQLite a los modelos publicados en `packages/shared`.

Aquí vive el trabajo que el encargo pone en el adaptador: el store devuelve
filas, el dominio de P1 recibe modelos del contrato, y nadie en medio reescribe
su firma. Ninguna función de este módulo calcula: convierte tipos y falla si una
fila no cumple el contrato, en vez de rellenar un campo ausente.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from uuid import UUID

from apps.api.canonical import parse_timestamp
from apps.api.store.json_columns import load, load_list
from packages.shared.domain.identity import SubjectProfile
from packages.shared.domain.observation import FieldObservation, FormSession, QuestionPresentation
from packages.shared.domain.outcome import OutcomeResolution
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.enums import VoiStatus


def instant(value: str) -> datetime:
    return parse_timestamp(value)


def optional_instant(value: str | None) -> datetime | None:
    return None if value is None else parse_timestamp(value)


def local_day(value: str) -> date:
    return date.fromisoformat(value)


def identifier(value: str | None) -> UUID | None:
    return None if value is None else UUID(str(value))


def field_observation(row: sqlite3.Row) -> FieldObservation:
    return FieldObservation(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        field_observation_id=UUID(row["field_observation_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=identifier(row["form_session_id"]),
        field_code=row["field_code"],
        value=load(row["value"]),
        source=row["source"],
        actor_id=UUID(row["actor_id"]),
        entry_mode=row["entry_mode"],
        data_origin=row["data_origin"],
        cohort_kind=row["cohort_kind"],
        effective_at=instant(row["effective_at"]),
        local_date=local_day(row["local_date"]),
        source_mapping_id=identifier(row["source_mapping_id"]),
    )


def form_session(row: sqlite3.Row) -> FormSession:
    return FormSession(
        form_session_id=UUID(row["form_session_id"]),
        tenant_id=UUID(row["tenant_id"]),
        subject_id=UUID(row["subject_id"]),
        actor_id=UUID(row["actor_id"]),
        source=row["source"],
        session_kind=row["session_kind"],
        status=row["status"],
        audit_mode=bool(row["audit_mode"]),
        form_policy_version=row["form_policy_version"],
        opened_at=instant(row["opened_at"]),
        submitted_at=optional_instant(row["submitted_at"]),
        prediction_episode_id=identifier(row["prediction_episode_id"]),
        linked_prediction_episode_id=identifier(row["linked_prediction_episode_id"]),
    )


def question_presentation(row: sqlite3.Row) -> QuestionPresentation:
    return QuestionPresentation(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["presented_at"]),
        question_presentation_id=UUID(row["question_presentation_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=UUID(row["form_session_id"]),
        field_code=row["field_code"],
        source=row["source"],
        highlighted=bool(row["highlighted"]),
        reason=row["reason"],
        presented_at=instant(row["presented_at"]),
        local_date=local_day(row["local_date"]),
        voi_nats=row["voi_nats"],
        voi_status=(
            VoiStatus.UNAVAILABLE_MODEL if row["voi_nats"] is None else VoiStatus.AVAILABLE
        ),
    )


def subject_profile(row: sqlite3.Row) -> SubjectProfile:
    return SubjectProfile(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        subject_profile_id=UUID(row["subject_profile_id"]),
        subject_id=UUID(row["subject_id"]),
        sensory_profile_tags=frozenset(load_list(row["sensory_profile_tags"])),
        communication_support_tags=frozenset(load_list(row["communication_support_tags"])),
        contraindication_tags=frozenset(load_list(row["contraindication_tags"])),
        care_mode=row["care_mode"],
        profile_version=row["profile_version"],
        effective_from=instant(row["effective_from"]),
        recorded_at=instant(row["recorded_at"]),
    )


def prediction_episode(row: sqlite3.Row) -> PredictionEpisode:
    return PredictionEpisode(
        prediction_episode_id=UUID(row["prediction_episode_id"]),
        tenant_id=UUID(row["tenant_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=UUID(row["form_session_id"]),
        role=row["role"],
        status=row["status"],
        as_of_at=instant(row["as_of_at"]),
        prediction_at=instant(row["prediction_at"]),
        target_start_at=instant(row["target_start_at"]),
        target_end_at=instant(row["target_end_at"]),
        capture_deadline_at=instant(row["capture_deadline_at"]),
        target_definition_version=row["target_definition_version"],
        care_mode=row["care_mode"],
        profile_version=row["profile_version"],
        cohort_kind=row["cohort_kind"],
        input_data_origin=row["input_data_origin"],
        feature_snapshot_id=identifier(row["feature_snapshot_id"]),
        created_at=instant(row["created_at"]),
    )


def outcome_resolution(row: sqlite3.Row) -> OutcomeResolution:
    return OutcomeResolution(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        outcome_resolution_id=UUID(row["outcome_resolution_id"]),
        prediction_episode_id=UUID(row["prediction_episode_id"]),
        status=row["status"],
        resolved_at=optional_instant(row["resolved_at"]),
        qualifying_report_id=identifier(row["qualifying_report_id"]),
        ever_conflicted=bool(row["ever_conflicted"]),
        resolution_version=int(row["resolution_version"]),
    )
