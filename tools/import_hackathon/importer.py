"""Escritura del conjunto NeuroHack en el esquema operativo.

Un registro diario produce la misma cadena que produciría un envío real:
`form_sessions` → `field_observations` → episodio primario → `outcome_requests`
→ `outcome_reports` → `outcome_resolutions`. Así el baseline no distingue lo
importado de lo capturado en la app, que es justamente lo que queremos medir.

El objetivo se opera contra `5_eventos_desregulacion_tutor.csv`: un episodio
resuelve `yes` cuando hay un evento dentro de su ventana de 24 h y `no` cuando
no lo hay. `nivel_regulacion_general_dia` **no** se usa como objetivo: es un
predictor del día y usarlo en ambos lados sería fuga.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from apps.api.canonical import canonical_timestamp
from apps.api.services.local_time import REFERENCE_ZONE
from apps.api.store.json_columns import dump
from packages.shared.constants import OUTCOME_CAPTURE_LIMIT_HOURS, TARGET_HORIZON_HOURS
from packages.shared.field_catalog import FieldCode
from tools.import_hackathon import mapping
from tools.import_hackathon.loader import Dataset, DysregulationEvent
from tools.seed import ids

MAPPING_NAME = "neurohack-2026-dataset"
MAPPING_VERSION = "1.0.0"
PROFILE_VERSION = "1.0.0"
FORM_POLICY_VERSION = "form-policy-0.3.0"
CARE_MODE = "home"

# Hora local en que el tutor cierra el registro del día. La ventana objetivo son
# las 24 h siguientes, así que el episodio del día D pregunta por D 20:00 → D+1
# 20:00 y no solapa con el del día siguiente.
CUTOFF_LOCAL_TIME = time(20, 0)


class ImportError_(RuntimeError):
    """La base no está en condiciones de recibir la importación."""


@dataclass(frozen=True, slots=True)
class ImportReport:
    subjects: int
    observations: int
    episodes: int
    positives: int
    negatives: int
    sessions_imported: int
    unmatched_events: tuple[str, ...]

    @property
    def prevalence(self) -> float:
        total = self.positives + self.negatives
        return self.positives / total if total else 0.0


def _id(*parts: str) -> str:
    raw = uuid5(NAMESPACE_URL, "neurohack-import:" + "|".join(parts)).hex
    return f"{raw[:8]}-{raw[8:12]}-4{raw[13:16]}-8{raw[17:20]}-{raw[20:32]}"


def _instant(day: date, moment: time = CUTOFF_LOCAL_TIME) -> datetime:
    """Instante UTC del reloj local de referencia (SPEC 5.2)."""

    return datetime.combine(day, moment, tzinfo=REFERENCE_ZONE).astimezone(UTC)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _events_by_case(dataset: Dataset) -> dict[str, list[DysregulationEvent]]:
    grouped: dict[str, list[DysregulationEvent]] = {}
    for event in dataset.events:
        grouped.setdefault(event.case_id, []).append(event)
    for events in grouped.values():
        events.sort(key=lambda event: event.occurred_at)
    return grouped


def _event_in_window(
    events: list[DysregulationEvent], start: datetime, end: datetime
) -> DysregulationEvent | None:
    """Primer evento en `[start, end)`. El CSV da hora local, no UTC."""

    for event in events:
        occurred = event.occurred_at.replace(tzinfo=REFERENCE_ZONE).astimezone(UTC)
        if start <= occurred < end:
            return event
    return None


def import_dataset(
    connection: sqlite3.Connection,
    dataset: Dataset,
    *,
    tenant_id: str = ids.TENANT_A,
    caregiver_id: str = ids.CAREGIVER_A,
    professional_id: str = ids.PROFESSIONAL_A,
    target_definition_version: str = ids.TARGET_DEMO_FIXTURE,
    ingested_at: datetime | None = None,
) -> ImportReport:
    """Importa el conjunto completo. Idempotente: todos los IDs son derivados."""

    moment = canonical_timestamp(ingested_at or datetime.now(UTC))
    _require_seeded(connection, tenant_id=tenant_id, target=target_definition_version)

    source_mapping_id = _upsert_source_mapping(connection, tenant_id=tenant_id, moment=moment)
    subject_ids = _upsert_subjects(
        connection, dataset, tenant_id=tenant_id, caregiver_id=caregiver_id, moment=moment
    )

    events = _events_by_case(dataset)
    matched: set[str] = set()
    observations = episodes = positives = negatives = 0

    for record in sorted(dataset.daily, key=lambda row: (row.case_id, row.day)):
        subject_id = subject_ids[record.case_id]
        as_of = _instant(record.day)
        target_end = as_of + timedelta(hours=TARGET_HORIZON_HOURS)
        deadline = as_of + timedelta(hours=OUTCOME_CAPTURE_LIMIT_HOURS)

        session_id = _id("session", record.record_id)
        _insert_form_session(
            connection,
            session_id=session_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            actor_id=caregiver_id,
            local_date=record.day,
            at=canonical_timestamp(as_of),
            session_kind="caregiver_daily",
            source="home",
        )

        for column, field_code, table in mapping.DAILY_COLUMNS:
            value = mapping.translate(table, getattr(record, field_code.value), column=column)
            _insert_observation(
                connection,
                observation_id=_id("obs", record.record_id, field_code.value),
                tenant_id=tenant_id,
                subject_id=subject_id,
                form_session_id=session_id,
                field_code=field_code.value,
                value=value,
                source="home",
                actor_id=caregiver_id,
                local_date=record.day,
                at=canonical_timestamp(as_of),
                ingested_at=moment,
                source_mapping_id=source_mapping_id,
            )
            observations += 1

        episode_id = _id("episode", record.record_id)
        _insert_episode(
            connection,
            episode_id=episode_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            form_session_id=session_id,
            as_of_at=canonical_timestamp(as_of),
            target_end_at=canonical_timestamp(target_end),
            capture_deadline_at=canonical_timestamp(deadline),
            target_definition_version=target_definition_version,
            created_at=moment,
        )
        connection.execute(
            "UPDATE form_sessions SET prediction_status = 'episode_created',"
            " prediction_episode_id = ? WHERE form_session_id = ?",
            (episode_id, session_id),
        )
        episodes += 1

        event = _event_in_window(events.get(record.case_id, []), as_of, target_end)
        if event is not None:
            matched.add(event.event_id)
            positives += 1
        else:
            negatives += 1

        _insert_outcome(
            connection,
            record_id=record.record_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            episode_id=episode_id,
            target_definition_version=target_definition_version,
            reporter_actor_id=caregiver_id,
            source_mapping_id=source_mapping_id,
            event=event,
            target_start_at=canonical_timestamp(as_of),
            target_end_at=canonical_timestamp(target_end),
            capture_deadline_at=canonical_timestamp(deadline),
            reported_at=canonical_timestamp(target_end),
            ingested_at=moment,
        )

    sessions_imported = _import_professional_sessions(
        connection,
        dataset,
        subject_ids=subject_ids,
        tenant_id=tenant_id,
        professional_id=professional_id,
        source_mapping_id=source_mapping_id,
        moment=moment,
    )

    return ImportReport(
        subjects=len(subject_ids),
        observations=observations,
        episodes=episodes,
        positives=positives,
        negatives=negatives,
        sessions_imported=sessions_imported,
        unmatched_events=tuple(
            sorted(event.event_id for event in dataset.events if event.event_id not in matched)
        ),
    )


def _require_seeded(connection: sqlite3.Connection, *, tenant_id: str, target: str) -> None:
    if (
        connection.execute("SELECT 1 FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
        is None
    ):
        raise ImportError_("la base no está sembrada: corré `python -m tools.seed` primero")
    if (
        connection.execute(
            "SELECT 1 FROM target_definition_versions WHERE target_definition_version = ?",
            (target,),
        ).fetchone()
        is None
    ):
        raise ImportError_(f"falta la definición de objetivo {target}")


def _upsert_source_mapping(connection: sqlite3.Connection, *, tenant_id: str, moment: str) -> str:
    """SPEC 4.4: una importación exige un mapping aprobado y versionado."""

    source_mapping_id = _id("mapping", MAPPING_NAME, MAPPING_VERSION)
    connection.execute(
        "INSERT OR IGNORE INTO source_mappings(source_mapping_id, tenant_id, name,"
        " mapping_version, approval_status, content_sha256, created_at)"
        " VALUES (?, ?, ?, ?, 'approved', ?, ?)",
        (
            source_mapping_id,
            tenant_id,
            MAPPING_NAME,
            MAPPING_VERSION,
            _sha(dump({column: dict(table) for column, _, table in mapping.DAILY_COLUMNS})),
            moment,
        ),
    )
    return source_mapping_id


def _upsert_subjects(
    connection: sqlite3.Connection,
    dataset: Dataset,
    *,
    tenant_id: str,
    caregiver_id: str,
    moment: str,
) -> dict[str, str]:
    """Un sujeto por caso, con perfil, consentimiento y grant de acceso.

    Sin consentimiento activo el baseline descarta el resultado
    (`consent_authorized`), así que el consentimiento es parte de la
    importación, no un paso aparte.
    """

    subject_ids: dict[str, str] = {}
    for case in dataset.cases:
        subject_id = _id("subject", case.case_id)
        subject_ids[case.case_id] = subject_id
        connection.execute(
            "INSERT OR IGNORE INTO subjects(subject_id, tenant_id, display_label,"
            " cohort_kind, created_at) VALUES (?, ?, ?, 'real_subject', ?)",
            (subject_id, tenant_id, case.case_id, moment),
        )
        connection.execute(
            "INSERT OR IGNORE INTO subject_profiles(subject_profile_id, tenant_id, subject_id,"
            " sensory_profile_tags, communication_support_tags, contraindication_tags,"
            " care_mode, profile_version, effective_from, recorded_at, supersedes_id,"
            " ingested_at) VALUES (?, ?, ?, ?, '[]', '[]', ?, ?, ?, ?, NULL, ?)",
            (
                _id("profile", case.case_id),
                tenant_id,
                subject_id,
                dump([case.sensory_profile]),
                CARE_MODE,
                PROFILE_VERSION,
                moment,
                moment,
                moment,
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO consents(consent_id, tenant_id, subject_id, grantor_actor_id,"
            " purpose, policy_version, granted_at, valid_from, valid_until, revoked_at,"
            " status, supersedes_id, ingested_at)"
            " VALUES (?, ?, ?, ?, 'operational_support', ?, ?, ?, NULL, NULL, 'active',"
            " NULL, ?)",
            (
                _id("consent", case.case_id),
                tenant_id,
                subject_id,
                caregiver_id,
                MAPPING_VERSION,
                moment,
                moment,
                moment,
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO subject_access_grants(subject_access_grant_id, tenant_id,"
            " subject_id, actor_id, capabilities, issuer_actor_id, valid_from, valid_until,"
            " revoked_at, status, supersedes_id, ingested_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'active', NULL, ?)",
            (
                _id("grant", case.case_id),
                tenant_id,
                subject_id,
                caregiver_id,
                dump(["subject_care"]),
                ids.TENANT_ADMIN_A,
                moment,
                moment,
            ),
        )
    return subject_ids


def _insert_form_session(
    connection: sqlite3.Connection,
    *,
    session_id: str,
    tenant_id: str,
    subject_id: str,
    actor_id: str,
    local_date: date,
    at: str,
    session_kind: str,
    source: str,
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO form_sessions(form_session_id, tenant_id, subject_id, actor_id,"
        " source, session_kind, status, audit_mode, audit_bucket, form_policy_version,"
        " local_date, opened_at, submitted_at, prediction_status, prediction_episode_id,"
        " linked_prediction_episode_id)"
        " VALUES (?, ?, ?, ?, ?, ?, 'submitted', 0, 0, ?, ?, ?, ?, NULL, NULL, NULL)",
        (
            session_id,
            tenant_id,
            subject_id,
            actor_id,
            source,
            session_kind,
            FORM_POLICY_VERSION,
            local_date.isoformat(),
            at,
            at,
        ),
    )


def _insert_observation(
    connection: sqlite3.Connection,
    *,
    observation_id: str,
    tenant_id: str,
    subject_id: str,
    form_session_id: str,
    field_code: str,
    value: str,
    source: str,
    actor_id: str,
    local_date: date,
    at: str,
    ingested_at: str,
    source_mapping_id: str,
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO field_observations(field_observation_id, tenant_id, subject_id,"
        " form_session_id, field_code, value, source, actor_id, entry_mode, data_origin,"
        " cohort_kind, effective_at, ingested_at, local_date, source_mapping_id,"
        " default_presentation_id, supersedes_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'imported_observed', 'real', 'real_subject',"
        " ?, ?, ?, ?, NULL, NULL)",
        (
            observation_id,
            tenant_id,
            subject_id,
            form_session_id,
            field_code,
            dump(value),
            source,
            actor_id,
            at,
            ingested_at,
            local_date.isoformat(),
            source_mapping_id,
        ),
    )


def _insert_episode(
    connection: sqlite3.Connection,
    *,
    episode_id: str,
    tenant_id: str,
    subject_id: str,
    form_session_id: str,
    as_of_at: str,
    target_end_at: str,
    capture_deadline_at: str,
    target_definition_version: str,
    created_at: str,
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO prediction_episodes(prediction_episode_id, tenant_id, subject_id,"
        " form_session_id, role, status, as_of_at, prediction_at, target_start_at,"
        " target_end_at, capture_deadline_at, target_definition_version, profile_version,"
        " care_mode, input_data_origin, created_at)"
        " VALUES (?, ?, ?, ?, 'primary', 'completed', ?, ?, ?, ?, ?, ?, ?, ?, 'real', ?)",
        (
            episode_id,
            tenant_id,
            subject_id,
            form_session_id,
            as_of_at,
            as_of_at,
            as_of_at,
            target_end_at,
            capture_deadline_at,
            target_definition_version,
            PROFILE_VERSION,
            CARE_MODE,
            created_at,
        ),
    )


def _insert_outcome(
    connection: sqlite3.Connection,
    *,
    record_id: str,
    tenant_id: str,
    subject_id: str,
    episode_id: str,
    target_definition_version: str,
    reporter_actor_id: str,
    source_mapping_id: str,
    event: DysregulationEvent | None,
    target_start_at: str,
    target_end_at: str,
    capture_deadline_at: str,
    reported_at: str,
    ingested_at: str,
) -> None:
    """Request + report + resolution. `yes` exige `occurred_at <= reported_at`."""

    connection.execute(
        "INSERT OR IGNORE INTO outcome_requests(outcome_request_id, tenant_id, subject_id,"
        " prediction_episode_id, target_definition_version, target_start_at, target_end_at,"
        " capture_deadline_at, eligible_reporter_roles, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _id("request", record_id),
            tenant_id,
            subject_id,
            episode_id,
            target_definition_version,
            target_start_at,
            target_end_at,
            capture_deadline_at,
            dump(["caregiver"]),
            ingested_at,
        ),
    )

    report_id = _id("report", record_id)
    occurred_at = (
        canonical_timestamp(event.occurred_at.replace(tzinfo=REFERENCE_ZONE).astimezone(UTC))
        if event is not None
        else None
    )
    connection.execute(
        "INSERT OR IGNORE INTO outcome_reports(outcome_report_id, tenant_id,"
        " prediction_episode_id, target_definition_version, reporter_actor_id, reporter_role,"
        " value, occurred_at, reported_at, timing_status, data_origin, intake_channel,"
        " source_mapping_id, supersedes_id, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, 'caregiver', ?, ?, ?, 'on_time', 'real', 'import', ?,"
        " NULL, ?)",
        (
            report_id,
            tenant_id,
            episode_id,
            target_definition_version,
            reporter_actor_id,
            "yes" if event is not None else "no",
            occurred_at,
            reported_at,
            source_mapping_id,
            ingested_at,
        ),
    )
    connection.execute(
        "INSERT OR IGNORE INTO outcome_resolutions(outcome_resolution_id, tenant_id,"
        " prediction_episode_id, status, resolved_at, qualifying_report_id, ever_conflicted,"
        " resolution_version, ingested_at, supersedes_id)"
        " VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, NULL)",
        (
            _id("resolution", record_id),
            tenant_id,
            episode_id,
            "yes" if event is not None else "no",
            reported_at,
            report_id,
            ingested_at,
        ),
    )


def _import_professional_sessions(
    connection: sqlite3.Connection,
    dataset: Dataset,
    *,
    subject_ids: dict[str, str],
    tenant_id: str,
    professional_id: str,
    source_mapping_id: str,
    moment: str,
) -> int:
    """Nivel de alerta final de cada sesión, como observación de terapia.

    Se importa el nivel final y no el inicial: el inicial describe con qué
    llegó el niño y el final con qué se fue, y es el segundo el que informa
    sobre el resto del día que el episodio está prediciendo.
    """

    imported = 0
    for session in dataset.sessions:
        subject_id = subject_ids[session.case_id]
        at = canonical_timestamp(_instant(session.day, time(12, 0)))
        session_id = _id("prof-session", session.session_id)
        _insert_form_session(
            connection,
            session_id=session_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            actor_id=professional_id,
            local_date=session.day,
            at=at,
            session_kind="professional_observation",
            source="therapy",
        )
        _insert_observation(
            connection,
            observation_id=_id("prof-obs", session.session_id, "alertness"),
            tenant_id=tenant_id,
            subject_id=subject_id,
            form_session_id=session_id,
            field_code=FieldCode.ALERTNESS.value,
            value=mapping.translate(
                mapping.ALERTNESS, session.alertness_final, column="nivel_alerta_final"
            ),
            source="therapy",
            actor_id=professional_id,
            local_date=session.day,
            at=at,
            ingested_at=moment,
            source_mapping_id=source_mapping_id,
        )
        imported += 1
    return imported


def import_from_directory(
    connection: sqlite3.Connection, directory: Path, **kwargs: object
) -> ImportReport:
    from tools.import_hackathon.loader import load_dataset

    return import_dataset(connection, load_dataset(directory), **kwargs)  # type: ignore[arg-type]
