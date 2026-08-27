"""Deterministic builders for P1 tests.

Fictional data only: no export row ever reaches a versioned test. IDs are
derived from a label so a failure names the row that broke.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from packages.shared.canonical import local_date
from packages.shared.domain.observation import FieldObservation
from packages.shared.domain.outcome import OutcomeReport, OutcomeWindow
from packages.shared.domain.prediction import CAPTURE_LIMIT, TARGET_HORIZON, PredictionEpisode
from packages.shared.enums import (
    CohortKind,
    DataOrigin,
    EntryMode,
    EpisodeRole,
    FieldCode,
    IntakeChannel,
    OutcomeReportValue,
    PredictionEpisodeStatus,
    Role,
    Source,
    TimingStatus,
)

NAMESPACE = uuid.UUID("11111111-2222-4333-8444-555555555555")
TENANT = uuid.uuid5(NAMESPACE, "tenant")
SUBJECT = uuid.uuid5(NAMESPACE, "subject")
ACTOR = uuid.uuid5(NAMESPACE, "actor")

# A fixed instant so every window in a test is reproducible.
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def ident(label: str) -> uuid.UUID:
    """A stable v4-shaped UUID derived from a label."""

    raw = bytearray(uuid.uuid5(NAMESPACE, label).bytes)
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


def observation(
    label: str,
    *,
    field_code: FieldCode = FieldCode.FOOD_CHANGES,
    value: Any = False,
    source: Source = Source.HOME,
    entry_mode: EntryMode = EntryMode.MANUAL_NO_DEFAULT,
    effective_at: datetime | None = None,
    ingested_at: datetime | None = None,
    supersedes_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID = TENANT,
    subject_id: uuid.UUID = SUBJECT,
    data_origin: DataOrigin = DataOrigin.REAL,
    source_mapping_id: uuid.UUID | None = None,
) -> FieldObservation:
    effective = effective_at or NOW
    return FieldObservation(
        field_observation_id=ident(label),
        tenant_id=tenant_id,
        subject_id=subject_id,
        field_code=field_code,
        value=value,
        source=source,
        actor_id=ACTOR,
        entry_mode=entry_mode,
        data_origin=data_origin,
        cohort_kind=CohortKind.REAL_SUBJECT.value,
        effective_at=effective,
        ingested_at=ingested_at or effective,
        local_date=local_date(effective),
        supersedes_id=supersedes_id,
        source_mapping_id=source_mapping_id,
    )


def episode(
    label: str = "episode",
    *,
    prediction_at: datetime = NOW,
    cohort_kind: CohortKind = CohortKind.REAL_SUBJECT,
    data_origin: DataOrigin = DataOrigin.REAL,
) -> PredictionEpisode:
    return PredictionEpisode(
        prediction_episode_id=ident(label),
        tenant_id=TENANT,
        subject_id=SUBJECT,
        form_session_id=ident(f"{label}-session"),
        role=EpisodeRole.PRIMARY,
        status=PredictionEpisodeStatus.COMPLETED,
        as_of_at=prediction_at,
        prediction_at=prediction_at,
        target_start_at=prediction_at,
        target_end_at=prediction_at + TARGET_HORIZON,
        capture_deadline_at=prediction_at + CAPTURE_LIMIT,
        target_definition_version="target-demo-1",
        care_mode="standard_support",
        profile_version="profile-1",
        cohort_kind=cohort_kind,
        input_data_origin=data_origin,
        created_at=prediction_at,
    )


def window(prediction_at: datetime = NOW) -> OutcomeWindow:
    return OutcomeWindow(
        target_start_at=prediction_at,
        target_end_at=prediction_at + TARGET_HORIZON,
        capture_deadline_at=prediction_at + CAPTURE_LIMIT,
    )


def report(
    label: str,
    *,
    value: OutcomeReportValue,
    reported_at: datetime,
    occurred_at: datetime | None = None,
    timing_status: TimingStatus | None = None,
    episode_id: uuid.UUID | None = None,
    reporter_role: Role = Role.CAREGIVER,
    supersedes_id: uuid.UUID | None = None,
    outcome_window: OutcomeWindow | None = None,
) -> OutcomeReport:
    from packages.shared.domain.outcome import classify_timing

    bounds = outcome_window or window()
    return OutcomeReport(
        outcome_report_id=ident(label),
        tenant_id=TENANT,
        prediction_episode_id=episode_id or ident("episode"),
        target_definition_version="target-demo-1",
        reporter_actor_id=ACTOR,
        reporter_role=reporter_role,
        value=value,
        occurred_at=occurred_at,
        reported_at=reported_at,
        timing_status=timing_status or classify_timing(reported_at, bounds),
        data_origin=DataOrigin.REAL,
        intake_channel=IntakeChannel.FORM,
        ingested_at=reported_at,
        supersedes_id=supersedes_id,
    )


def hours(count: float) -> timedelta:
    return timedelta(hours=count)
