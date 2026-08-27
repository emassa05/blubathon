"""Dataset snapshots, training runs, model versions and evaluation reports.

Every metric states its origin, dataset hash and model, and a metric without
support is `not_estimable` rather than zero (SPEC 14.3, CONVENTIONS 9.4).
Synthetic metrics always carry `simulation_only` where a reader can see it.

Development out-of-fold results never move a model to `shadow_evaluated`: that
transition needs a preregistered prospective period (SPEC 14.4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.domain.base import (
    FaroModel,
    Interval,
    Sha256Hex,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    DataOrigin,
    EvaluationReportStatus,
    IntendedUse,
    MetricStatus,
    ModelState,
    NotTrainableReason,
    Source,
    TrackId,
    TrainingRunStatus,
)


class DatasetSnapshot(FaroModel):
    """Immutable, hashed, and separated by origin. Real and synthetic never mix."""

    dataset_snapshot_id: UUID
    tenant_id: UUID
    data_origin: DataOrigin
    target_definition_version: VersionLabel
    cutoff_at: UtcDatetime
    episode_ids: tuple[UUID, ...] = ()
    observation_ids: tuple[UUID, ...] = ()
    outcome_resolution_ids: tuple[UUID, ...] = ()
    consent_ids: tuple[UUID, ...] = ()
    subject_count: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    content_sha256: Sha256Hex
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _counts_fit_the_episodes(self) -> Self:
        if self.positive_count + self.negative_count > len(self.episode_ids):
            raise ValueError("labelled episodes cannot exceed the episodes in the snapshot")
        return self

    @property
    def has_both_classes(self) -> bool:
        return self.positive_count > 0 and self.negative_count > 0


class ChallengerTrainingProtocolVersion(FaroModel):
    """Optimiser settings fixed before a run, not per-run flags (SPEC 8.4)."""

    protocol_version: VersionLabel
    optimizer: str
    tolerance: float = Field(gt=0)
    max_iterations: int = Field(gt=0)
    l2_grid: tuple[float, ...] = Field(min_length=1)
    tie_tolerance: float = Field(gt=0)
    library_versions: dict[str, str]
    content_sha256: Sha256Hex


class EvaluationProtocolVersion(FaroModel):
    """Splits, seeds, interval method and estimability rules, all versioned."""

    protocol_version: VersionLabel
    outer_split: str
    inner_split: str
    random_seed: int
    bootstrap_replicates: int = Field(gt=0)
    interval_level: float = Field(gt=0, lt=1)
    min_valid_bootstrap_fraction: float = Field(gt=0, le=1)
    group_min_subjects: int = Field(ge=0)
    group_min_positives: int = Field(ge=0)
    group_min_negatives: int = Field(ge=0)
    library_versions: dict[str, str]
    reveal_schedule_sha256: Sha256Hex | None = None
    content_sha256: Sha256Hex


class TrainingRun(FaroModel):
    """A run that produced a candidate, or an honest reason it produced none."""

    training_run_id: UUID
    tenant_id: UUID
    dataset_snapshot_id: UUID
    track_id: TrackId
    status: TrainingRunStatus
    not_trainable_reason: NotTrainableReason | None = None
    challenger_protocol_version: VersionLabel | None = None
    code_version: str
    dependency_versions: dict[str, str]
    dataset_sha256: Sha256Hex
    consent_reauthorized: bool
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    model_version: VersionLabel | None = None

    @model_validator(mode="after")
    def _status_carries_its_evidence(self) -> Self:
        if self.status is TrainingRunStatus.NOT_TRAINABLE:
            if self.not_trainable_reason is None:
                raise ValueError("a not_trainable run states why")
            if self.model_version is not None:
                raise ValueError("a not_trainable run creates no model version")
        elif self.not_trainable_reason is not None:
            raise ValueError("only a not_trainable run carries a not_trainable reason")

        if self.status is TrainingRunStatus.COMPLETED and self.model_version is None:
            raise ValueError("a completed run names the model version it produced")
        if not self.consent_reauthorized and self.status is TrainingRunStatus.COMPLETED:
            raise ValueError("a run cannot complete without reauthorised consent")
        return self


class ModelVersion(FaroModel):
    """A trained artifact and the only states it is allowed to be in.

    There is no automatic promotion to an operational champion in v0.3.
    """

    model_version: VersionLabel
    track_id: TrackId
    training_run_id: UUID | None = None
    training_data_origin: DataOrigin
    intended_use: IntendedUse
    state: ModelState
    artifact_sha256: Sha256Hex | None = None
    created_at: UtcDatetime
    suspended_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _real_models_stay_in_shadow(self) -> Self:
        challenger_states = {
            ModelState.CANDIDATE,
            ModelState.VALIDATED_OFFLINE,
            ModelState.SHADOW,
            ModelState.SHADOW_EVALUATED,
        }
        if (
            self.track_id is TrackId.REAL_LOGIT_CHALLENGER_V1
            and self.state in challenger_states
            and self.intended_use is not IntendedUse.SHADOW_EVALUATION
        ):
            raise ValueError("the challenger is a shadow evaluation artifact in v0.3")
        if self.state is ModelState.SUSPENDED_FOR_CONSENT_REVIEW:
            if self.training_data_origin is not DataOrigin.REAL:
                raise ValueError("consent suspension only applies to real artifacts")
            if self.suspended_at is None:
                raise ValueError("a suspension records when it happened")
        return self


class MetricValue(FaroModel):
    """A number with its estimability, or an explicit reason there is none."""

    name: str
    status: MetricStatus
    value: float | None = None
    interval: Interval | None = None
    not_estimable_reason: str | None = None
    denominator: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _estimability_matches_its_content(self) -> Self:
        if self.status is MetricStatus.ESTIMATED:
            if self.value is None:
                raise ValueError("an estimated metric has a value")
            if self.not_estimable_reason is not None:
                raise ValueError("an estimated metric carries no not_estimable reason")
        else:
            if self.value is not None or self.interval is not None:
                raise ValueError("a not_estimable metric carries no value or interval")
            if not self.not_estimable_reason:
                raise ValueError("a not_estimable metric states why")
        return self


class GroupMetric(FaroModel):
    """A per-group metric, suppressed unless the privacy minimums are met."""

    group_kind: str
    group_value: str
    subject_count: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    suppressed: bool
    metrics: tuple[MetricValue, ...] = ()

    @model_validator(mode="after")
    def _suppression_hides_everything(self) -> Self:
        if self.suppressed and self.metrics:
            raise ValueError("a suppressed group publishes no metrics, not even indirectly")
        return self


class SourceMetric(FaroModel):
    """Metrics broken down by observation context (SPEC 14.3)."""

    source: Source
    metrics: tuple[MetricValue, ...] = ()


class AbstentionBreakdown(FaroModel):
    """Abstention rate per reason, over the same denominator as coverage."""

    reason: str
    count: int = Field(ge=0)
    rate: float = Field(ge=0.0, le=1.0)


class EvaluationReport(FaroModel):
    """One report, one exact target definition version. No pooling in v0.3."""

    evaluation_report_id: UUID
    tenant_id: UUID
    model_version: VersionLabel
    track_id: TrackId
    dataset_snapshot_id: UUID
    dataset_sha256: Sha256Hex
    data_origin: DataOrigin
    intended_use: IntendedUse
    target_definition_version: VersionLabel
    protocol_version: VersionLabel
    status: EvaluationReportStatus
    metrics: tuple[MetricValue, ...] = ()
    group_metrics: tuple[GroupMetric, ...] = ()
    source_metrics: tuple[SourceMetric, ...] = ()
    decision_coverage: MetricValue | None = None
    abstentions: tuple[AbstentionBreakdown, ...] = ()
    limitations_es: tuple[str, ...] = Field(min_length=1)
    created_at: UtcDatetime
    published_at: UtcDatetime | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _origin_and_use_agree(self) -> Self:
        if (
            self.data_origin is DataOrigin.SYNTHETIC
            and self.intended_use is not IntendedUse.SIMULATION_ONLY
        ):
            raise ValueError("a synthetic report is simulation_only and says so")
        if self.status is EvaluationReportStatus.PUBLISHED and self.published_at is None:
            raise ValueError("a published report records when it was published")
        return self

    @property
    def is_simulation_only(self) -> bool:
        return self.intended_use is IntendedUse.SIMULATION_ONLY


class ReleaseManifest(FaroModel):
    """Implementation, corpus, target and catalogue status, declared separately.

    Without a legally usable corpus M4 and the DoD stay blocked; without an
    authorised reviewer the catalogue can only be `blocked_clinical_review`
    (SPEC 20).
    """

    spec_version: VersionLabel
    contract_version: VersionLabel
    implementation_status: str
    corpus_status: str
    target_definition_status: str
    catalog_status: str
    generated_at: UtcDatetime
    notes_es: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _catalog_status_is_one_of_the_declared_values(self) -> Self:
        allowed = {"catalog_enabled", "blocked_clinical_review", "blocked_corpus", "not_ready"}
        if self.catalog_status not in allowed:
            raise ValueError(f"catalog_status must be one of {sorted(allowed)}")
        return self


def development_result_cannot_promote(state: ModelState) -> bool:
    """Guard for SPEC 14.4: offline OOF never reaches `shadow_evaluated`."""

    return state is not ModelState.SHADOW_EVALUATED


def now_is_after(moment: datetime, reference: datetime) -> bool:
    return moment > reference
