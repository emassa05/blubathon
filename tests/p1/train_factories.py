"""Fictional episodes, resolutions, consents and observations for M5 tests.

Invented data only. No export row ever reaches a versioned test (CONVENTIONS 15).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from packages.shared.canonical import local_date
from packages.shared.domain.identity import Consent
from packages.shared.domain.observation import FieldObservation
from packages.shared.domain.outcome import OutcomeResolution
from packages.shared.domain.prediction import CAPTURE_LIMIT, TARGET_HORIZON, PredictionEpisode
from packages.shared.enums import (
    AuthorizationStatus,
    CohortKind,
    ConsentPurpose,
    DataOrigin,
    EntryMode,
    EpisodeRole,
    FieldCode,
    OutcomeResolutionStatus,
    PredictionEpisodeStatus,
    Source,
)
from tests.p1.factories import ACTOR, TENANT, ident

RUN_AT = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
TARGET_VERSION = "target-demo-1"
CARE_MODE = "standard_support"


def subject(label: str) -> uuid.UUID:
    return ident(f"subject:{label}")


def episode(
    label: str,
    *,
    subject_id: uuid.UUID,
    prediction_at: datetime,
    role: EpisodeRole = EpisodeRole.PRIMARY,
    data_origin: DataOrigin = DataOrigin.REAL,
    cohort_kind: CohortKind = CohortKind.REAL_SUBJECT,
    target_definition_version: str = TARGET_VERSION,
    care_mode: str | None = CARE_MODE,
) -> PredictionEpisode:
    return PredictionEpisode(
        prediction_episode_id=ident(f"episode:{label}"),
        tenant_id=TENANT,
        subject_id=subject_id,
        form_session_id=ident(f"session:{label}"),
        role=role,
        status=PredictionEpisodeStatus.COMPLETED,
        as_of_at=prediction_at,
        prediction_at=prediction_at,
        target_start_at=prediction_at,
        target_end_at=prediction_at + TARGET_HORIZON,
        capture_deadline_at=prediction_at + CAPTURE_LIMIT,
        target_definition_version=target_definition_version,
        care_mode=care_mode,
        profile_version="profile-1",
        cohort_kind=cohort_kind,
        input_data_origin=data_origin,
        created_at=prediction_at,
    )


def resolution(
    label: str,
    *,
    episode_id: uuid.UUID,
    status: OutcomeResolutionStatus,
    resolved_at: datetime | None,
    ever_conflicted: bool = False,
    ingested_at: datetime | None = None,
    supersedes_id: uuid.UUID | None = None,
    version: int = 1,
) -> OutcomeResolution:
    conclusive = status in {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}
    return OutcomeResolution(
        outcome_resolution_id=ident(f"resolution:{label}"),
        tenant_id=TENANT,
        prediction_episode_id=episode_id,
        status=status,
        resolved_at=resolved_at,
        qualifying_report_id=ident(f"report:{label}") if conclusive else None,
        ever_conflicted=ever_conflicted,
        resolution_version=version,
        ingested_at=ingested_at or (resolved_at or RUN_AT),
        supersedes_id=supersedes_id,
    )


def consent(
    label: str,
    *,
    subject_id: uuid.UUID,
    purpose: ConsentPurpose = ConsentPurpose.SECONDARY_MODEL_USE,
    granted_at: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    revoked_at: datetime | None = None,
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE,
    supersedes_id: uuid.UUID | None = None,
) -> Consent:
    return Consent(
        consent_id=ident(f"consent:{label}"),
        tenant_id=TENANT,
        subject_id=subject_id,
        grantor_actor_id=ACTOR,
        purpose=purpose,
        policy_version="consent-0.3.0",
        granted_at=granted_at,
        valid_from=granted_at,
        revoked_at=revoked_at,
        status=status,
        ingested_at=granted_at,
        supersedes_id=supersedes_id,
    )


def observation(
    label: str,
    *,
    subject_id: uuid.UUID,
    field_code: FieldCode,
    value: str,
    effective_at: datetime,
    source: Source = Source.HOME,
    entry_mode: EntryMode = EntryMode.MANUAL_NO_DEFAULT,
    data_origin: DataOrigin = DataOrigin.REAL,
) -> FieldObservation:
    return FieldObservation(
        field_observation_id=ident(f"observation:{label}"),
        tenant_id=TENANT,
        subject_id=subject_id,
        field_code=field_code,
        value=value,
        source=source,
        actor_id=ACTOR,
        entry_mode=entry_mode,
        data_origin=data_origin,
        cohort_kind=CohortKind.REAL_SUBJECT.value,
        effective_at=effective_at,
        ingested_at=effective_at,
        local_date=local_date(effective_at),
    )


def predictor_history(
    subject_id: uuid.UUID,
    *,
    days: int,
    until: datetime,
    sleep_values: tuple[str, ...] = ("restorative", "interrupted"),
    regulation_values: tuple[str, ...] = ("excellent", "stable_with_support"),
    prefix: str = "",
) -> tuple[FieldObservation, ...]:
    """Enough daily history for the personal rates to exist (C22)."""

    rows: list[FieldObservation] = []
    for offset in range(1, days + 1):
        moment = until - timedelta(days=offset)
        rows.append(
            observation(
                f"{prefix}sleep-{subject_id}-{offset}",
                subject_id=subject_id,
                field_code=FieldCode.SLEEP_QUALITY,
                value=sleep_values[offset % len(sleep_values)],
                effective_at=moment,
            )
        )
        rows.append(
            observation(
                f"{prefix}regulation-{subject_id}-{offset}",
                subject_id=subject_id,
                field_code=FieldCode.DAILY_REGULATION_STATE,
                value=regulation_values[offset % len(regulation_values)],
                effective_at=moment,
            )
        )
    return tuple(rows)
