"""Immutable, hashed dataset snapshots, separated by origin (SPEC 14.2, 10.5).

Real and synthetic never share a snapshot, and the check is not a filter: a
synthetic row offered to a real snapshot raises, because silently dropping it
would hide the fact that something upstream mixed them (INV-17).

Membership is the SPEC 14.2 list, applied literally: primary episodes only, one
exact target definition version, a conclusive resolution that was never
conflicted, a qualifying report, compatible consent, and a label strictly after
the cutoff the snapshot projects to.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ml.errors import OriginMixError
from packages.shared.canonical import content_hash
from packages.shared.domain.evaluation import DatasetSnapshot
from packages.shared.domain.identity import Consent
from packages.shared.domain.observation import FieldObservation
from packages.shared.domain.outcome import OutcomeResolution, qualifies_for_primary_dataset
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.enums import DataOrigin, EpisodeRole, OutcomeResolutionStatus
from packages.shared.projection import project_as_of, unique_active
from tools.train.consent import authorize_secondary_model_use

DATASET_ARTIFACT = "dataset_snapshot"
DATASET_SCHEMA_VERSION = "dataset-snapshot-0.3.0"


@dataclass(frozen=True, slots=True)
class SnapshotInputs:
    """Everything a snapshot may read, already loaded by the caller."""

    tenant_id: UUID
    data_origin: DataOrigin
    target_definition_version: str
    cutoff_at: datetime
    episodes: tuple[PredictionEpisode, ...] = ()
    resolutions: tuple[OutcomeResolution, ...] = ()
    observations: tuple[FieldObservation, ...] = ()
    consents: tuple[Consent, ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotBuild:
    """The snapshot plus the rows behind it, for the run that follows."""

    snapshot: DatasetSnapshot
    episodes: tuple[PredictionEpisode, ...]
    resolutions: tuple[OutcomeResolution, ...]
    observations: tuple[FieldObservation, ...]
    excluded: tuple[tuple[UUID, str], ...]

    @property
    def subject_ids(self) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(episode.subject_id for episode in self.episodes))


def _assert_single_origin(inputs: SnapshotInputs) -> None:
    """A snapshot of one origin refuses a row of the other, loudly (INV-17)."""

    for episode in inputs.episodes:
        if episode.input_data_origin is not inputs.data_origin:
            raise OriginMixError(
                f"episode {episode.prediction_episode_id} is "
                f"{episode.input_data_origin.value} in a {inputs.data_origin.value} snapshot"
            )
    for observation in inputs.observations:
        if observation.data_origin is not inputs.data_origin:
            raise OriginMixError(
                f"observation {observation.field_observation_id} is "
                f"{observation.data_origin.value} in a {inputs.data_origin.value} snapshot"
            )


def build_dataset_snapshot(
    inputs: SnapshotInputs, *, dataset_snapshot_id: UUID, created_at: datetime
) -> SnapshotBuild:
    """Project to the cutoff, apply SPEC 14.2 membership, and hash the result."""

    _assert_single_origin(inputs)

    resolutions = project_as_of(inputs.resolutions, inputs.cutoff_at)
    active = unique_active(resolutions, key=lambda row: row.prediction_episode_id)
    observations = project_as_of(inputs.observations, inputs.cutoff_at)

    kept: list[PredictionEpisode] = []
    kept_resolutions: list[OutcomeResolution] = []
    excluded: list[tuple[UUID, str]] = []

    consent_ids: tuple[UUID, ...] = ()
    authorized_subjects: frozenset[UUID] = frozenset()
    if inputs.data_origin is DataOrigin.REAL:
        candidate_subjects = tuple(dict.fromkeys(episode.subject_id for episode in inputs.episodes))
        per_subject = {
            subject_id: authorize_secondary_model_use(
                inputs.consents, subject_ids=(subject_id,), at=inputs.cutoff_at
            )
            for subject_id in candidate_subjects
        }
        authorized_subjects = frozenset(
            subject_id for subject_id, result in per_subject.items() if result.authorized
        )
        consent_ids = tuple(
            sorted(
                {
                    consent_id
                    for subject_id in authorized_subjects
                    for consent_id in per_subject[subject_id].consent_ids
                },
                key=str,
            )
        )

    for episode in sorted(inputs.episodes, key=lambda item: str(item.prediction_episode_id)):
        reason = _membership_failure(
            episode,
            inputs=inputs,
            active=active,
            authorized_subjects=authorized_subjects,
        )
        if reason is not None:
            excluded.append((episode.prediction_episode_id, reason))
            continue
        kept.append(episode)
        kept_resolutions.append(active.rows[episode.prediction_episode_id])

    kept_subjects = {episode.subject_id for episode in kept}
    kept_observations = tuple(row for row in observations.leaves if row.subject_id in kept_subjects)

    positives = sum(
        1 for resolution in kept_resolutions if resolution.status is OutcomeResolutionStatus.YES
    )
    negatives = len(kept_resolutions) - positives

    episode_ids = tuple(sorted((episode.prediction_episode_id for episode in kept), key=str))
    observation_ids = tuple(
        sorted((row.field_observation_id for row in kept_observations), key=str)
    )
    resolution_ids = tuple(sorted((row.outcome_resolution_id for row in kept_resolutions), key=str))

    payload = {
        "tenant_id": str(inputs.tenant_id),
        "data_origin": inputs.data_origin.value,
        "target_definition_version": inputs.target_definition_version,
        "cutoff_at": inputs.cutoff_at,
        "episode_ids": [str(value) for value in episode_ids],
        "observation_ids": [str(value) for value in observation_ids],
        "outcome_resolution_ids": [str(value) for value in resolution_ids],
        "consent_ids": [str(value) for value in consent_ids],
        "positive_count": positives,
        "negative_count": negatives,
    }

    snapshot = DatasetSnapshot(
        dataset_snapshot_id=dataset_snapshot_id,
        tenant_id=inputs.tenant_id,
        data_origin=inputs.data_origin,
        target_definition_version=inputs.target_definition_version,
        cutoff_at=inputs.cutoff_at,
        episode_ids=episode_ids,
        observation_ids=observation_ids,
        outcome_resolution_ids=resolution_ids,
        consent_ids=consent_ids,
        subject_count=len(kept_subjects),
        positive_count=positives,
        negative_count=negatives,
        content_sha256=content_hash(DATASET_ARTIFACT, DATASET_SCHEMA_VERSION, payload),
        created_at=created_at,
    )
    return SnapshotBuild(
        snapshot=snapshot,
        episodes=tuple(kept),
        resolutions=tuple(kept_resolutions),
        observations=kept_observations,
        excluded=tuple(excluded),
    )


def _membership_failure(
    episode: PredictionEpisode,
    *,
    inputs: SnapshotInputs,
    active,
    authorized_subjects: frozenset[UUID],
) -> str | None:
    """The first SPEC 14.2 condition this episode fails, or `None`."""

    if episode.tenant_id != inputs.tenant_id:
        return "other_tenant"
    if episode.role is not EpisodeRole.PRIMARY:
        return "not_primary"
    if episode.target_definition_version != inputs.target_definition_version:
        return "other_target_definition_version"
    if episode.as_of_at > inputs.cutoff_at:
        return "after_cutoff"
    if inputs.data_origin is DataOrigin.REAL and episode.subject_id not in authorized_subjects:
        return "consent_not_authorized"

    resolution = active.rows.get(episode.prediction_episode_id)
    if resolution is None:
        return "no_active_resolution"
    if resolution.ever_conflicted:
        return "ever_conflicted"
    if not qualifies_for_primary_dataset(resolution):
        return "not_conclusive"
    if resolution.resolved_at is None or resolution.resolved_at <= episode.target_start_at:
        # SPEC 14.2: the label is strictly after the snapshot cutoff of its own
        # episode, never simultaneous with it.
        return "label_not_after_cutoff"
    return None
