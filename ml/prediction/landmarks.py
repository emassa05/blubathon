"""Landmarks: one row per primary episode, built only from its own past.

A landmark is the moment a prediction was due. Everything the challenger sees at
that moment -- the baseline offset and the two personal deviations -- is derived
from history that was already resolved and ingested at `as_of_at`, and from
nothing else.

That is the point of the reveal schedule: it records when each outcome became
known, so an evaluation can prove that a label used to build a feature was
revealed before the landmark that used it, and that no label ever fitted a
coefficient or chose a penalty.

A landmark whose history does not meet the minimums is `not_estimable`. It is
kept, with its reason, rather than dropped silently.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ml.prediction.baseline import BaselineCandidate, build_personal_baseline
from ml.prediction.challenger import ChallengerRow, encode_predictor, personal_predictor_rate
from packages.shared.canonical import content_hash, local_date
from packages.shared.domain.observation import PRIMARY_REAL_MODEL_MODES, FieldObservation
from packages.shared.domain.outcome import OutcomeResolution, qualifies_for_primary_dataset
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.enums import (
    DataOrigin,
    EpisodeRole,
    FieldCode,
    OutcomeResolutionStatus,
    Source,
)
from packages.shared.projection import project_as_of, unique_active

REVEAL_SCHEDULE_ARTIFACT = "reveal_schedule"
REVEAL_SCHEDULE_VERSION = "reveal-schedule-0.3.0"

CHALLENGER_PREDICTORS: tuple[FieldCode, ...] = (
    FieldCode.SLEEP_QUALITY,
    FieldCode.DAILY_REGULATION_STATE,
)


@dataclass(frozen=True, slots=True)
class RevealEvent:
    """When one episode's outcome became usable as history."""

    prediction_episode_id: UUID
    subject_id: UUID
    resolved_at: datetime
    ingested_at: datetime
    label: int


@dataclass(frozen=True, slots=True)
class Landmark:
    """One episode as a dataset row, or the reason it is not estimable."""

    prediction_episode_id: UUID
    subject_id: UUID
    as_of_at: datetime
    source: Source
    label: int
    row: ChallengerRow | None = None
    not_estimable_reason: str | None = None

    @property
    def is_estimable(self) -> bool:
        return self.row is not None


def reveal_schedule(
    episodes: Iterable[PredictionEpisode], resolutions: Iterable[OutcomeResolution]
) -> tuple[RevealEvent, ...]:
    """Every conclusive outcome with the instant it was revealed, in order."""

    by_episode = {episode.prediction_episode_id: episode for episode in episodes}
    events: list[RevealEvent] = []
    for resolution in resolutions:
        episode = by_episode.get(resolution.prediction_episode_id)
        if episode is None or not qualifies_for_primary_dataset(resolution):
            continue
        if resolution.resolved_at is None:
            continue
        events.append(
            RevealEvent(
                prediction_episode_id=resolution.prediction_episode_id,
                subject_id=episode.subject_id,
                resolved_at=resolution.resolved_at,
                ingested_at=resolution.ingested_at,
                label=1 if resolution.status is OutcomeResolutionStatus.YES else 0,
            )
        )
    events.sort(key=lambda event: (event.resolved_at, str(event.prediction_episode_id)))
    return tuple(events)


def reveal_schedule_sha256(events: Sequence[RevealEvent]) -> str:
    """The hash an `EvaluationProtocolVersion` persists."""

    payload = [
        {
            "prediction_episode_id": str(event.prediction_episode_id),
            "subject_id": str(event.subject_id),
            "resolved_at": event.resolved_at,
            "ingested_at": event.ingested_at,
            "label": event.label,
        }
        for event in events
    ]
    return content_hash(REVEAL_SCHEDULE_ARTIFACT, REVEAL_SCHEDULE_VERSION, payload)


def _deviation(
    observations: Sequence[FieldObservation],
    *,
    episode: PredictionEpisode,
    source: Source,
    field_code: FieldCode,
) -> tuple[float | None, str | None]:
    """Today's encoded predictor minus the subject's own previous rate."""

    projection = project_as_of(observations, episode.as_of_at)
    same_day = [
        row
        for row in projection.leaves
        if (row.tenant_id, row.subject_id, row.source, row.field_code)
        == (episode.tenant_id, episode.subject_id, source, field_code)
        and row.local_date == local_date(episode.as_of_at)
        and row.entry_mode in PRIMARY_REAL_MODEL_MODES
    ]
    grouped = unique_active(
        project_as_of(same_day, episode.as_of_at), key=lambda row: row.field_code
    )
    if not grouped.is_clean:
        return None, "feature_conflict"
    current_row = grouped.rows.get(field_code)
    if current_row is None:
        return None, "predictor_missing"
    current = encode_predictor(field_code, current_row.value)
    if current is None:
        return None, "predictor_missing"

    rate = personal_predictor_rate(
        observations,
        tenant_id=episode.tenant_id,
        subject_id=episode.subject_id,
        source=source,
        field_code=field_code,
        as_of_at=episode.as_of_at,
    )
    if rate.rate is None:
        return None, rate.reason
    return current - rate.rate, None


def build_landmarks(
    *,
    episodes: Iterable[PredictionEpisode],
    resolutions: Iterable[OutcomeResolution],
    observations: Iterable[FieldObservation],
    consented_subject_ids: frozenset[UUID],
    target_definition_version: str,
    source: Source = Source.HOME,
) -> tuple[Landmark, ...]:
    """One landmark per eligible primary episode, ordered by cutoff then id."""

    episode_list = [
        episode
        for episode in episodes
        if episode.role is EpisodeRole.PRIMARY
        and episode.input_data_origin is DataOrigin.REAL
        and episode.target_definition_version == target_definition_version
        and episode.subject_id in consented_subject_ids
    ]
    resolution_list = tuple(resolutions)
    observation_list = tuple(observations)
    by_episode = {
        resolution.prediction_episode_id: resolution
        for resolution in resolution_list
        if qualifies_for_primary_dataset(resolution)
    }

    landmarks: list[Landmark] = []
    for episode in sorted(
        episode_list, key=lambda item: (item.as_of_at, str(item.prediction_episode_id))
    ):
        resolution = by_episode.get(episode.prediction_episode_id)
        if resolution is None:
            continue
        label = 1 if resolution.status is OutcomeResolutionStatus.YES else 0

        # The baseline sees only this subject's outcomes already resolved and
        # ingested at this cutoff. A later correction never reaches backwards.
        history = [
            BaselineCandidate(
                episode=other,
                resolution=by_episode[other.prediction_episode_id],
                consent_authorized=other.subject_id in consented_subject_ids,
            )
            for other in episode_list
            if other.prediction_episode_id != episode.prediction_episode_id
            and other.prediction_episode_id in by_episode
        ]
        baseline = build_personal_baseline(
            history,
            as_of_at=episode.as_of_at,
            subject_id=episode.subject_id,
            care_mode=episode.care_mode,
            target_definition_version=target_definition_version,
        )
        if baseline.probability is None:
            landmarks.append(
                Landmark(
                    prediction_episode_id=episode.prediction_episode_id,
                    subject_id=episode.subject_id,
                    as_of_at=episode.as_of_at,
                    source=source,
                    label=label,
                    not_estimable_reason=(
                        baseline.abstention_reasons[0].value
                        if baseline.abstention_reasons
                        else "baseline_unavailable"
                    ),
                )
            )
            continue

        deviations: list[float] = []
        reason: str | None = None
        for field_code in CHALLENGER_PREDICTORS:
            value, failure = _deviation(
                observation_list, episode=episode, source=source, field_code=field_code
            )
            if value is None:
                reason = failure
                break
            deviations.append(value)

        if reason is not None:
            landmarks.append(
                Landmark(
                    prediction_episode_id=episode.prediction_episode_id,
                    subject_id=episode.subject_id,
                    as_of_at=episode.as_of_at,
                    source=source,
                    label=label,
                    not_estimable_reason=reason,
                )
            )
            continue

        landmarks.append(
            Landmark(
                prediction_episode_id=episode.prediction_episode_id,
                subject_id=episode.subject_id,
                as_of_at=episode.as_of_at,
                source=source,
                label=label,
                row=ChallengerRow(
                    subject_id=episode.subject_id,
                    p_base=baseline.probability,
                    sleep_deviation=deviations[0],
                    regulation_deviation=deviations[1],
                    label=label,
                ),
            )
        )
    return tuple(landmarks)


def estimable_rows(landmarks: Iterable[Landmark]) -> tuple[ChallengerRow, ...]:
    """The rows a training run may fit, in landmark order."""

    return tuple(landmark.row for landmark in landmarks if landmark.row is not None)
