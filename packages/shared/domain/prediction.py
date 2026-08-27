"""Target definitions, episodes, snapshots and per-track outputs.

The window is fixed by the server at submit time and never moves:
`as_of_at = prediction_at = submitted_at`, the target is `(prediction_at,
prediction_at + 24h]`, and capture closes 24 hours after that.

`confidence` is deliberately absent from `PredictionOutput`: it has no single
meaning across a designed simulation, a personal Beta posterior and a shadow
challenger, and a field that means three things is not a contract.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.constants import (
    OUTCOME_CAPTURE_LIMIT_HOURS,
    TARGET_HORIZON_HOURS,
)
from packages.shared.domain.base import (
    BlubathonModel,
    Interval,
    NonNegativeFloat,
    Probability,
    Sha256Hex,
    SpanishText,
    Tag,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    ApprovalStatus,
    CohortKind,
    DataOrigin,
    EpisodeRole,
    EstimateKind,
    FieldCode,
    IntendedUse,
    IntervalMethod,
    PredictionAbstentionReason,
    PredictionEpisodeStatus,
    PredictionStatus,
    Role,
    TargetScope,
    TrackId,
    VoiStatus,
)

TARGET_HORIZON = timedelta(hours=TARGET_HORIZON_HOURS)
CAPTURE_LIMIT = timedelta(hours=OUTCOME_CAPTURE_LIMIT_HOURS)

TRACK_INTENDED_USE: dict[TrackId, IntendedUse] = {
    TrackId.SYNTHETIC_REFERENCE_V021: IntendedUse.SIMULATION_ONLY,
    TrackId.REAL_PERSONAL_BASELINE_V1: IntendedUse.OPERATIONAL_SUPPORT,
    TrackId.REAL_LOGIT_CHALLENGER_V1: IntendedUse.OPERATIONAL_SUPPORT,
}
TRACK_ESTIMATE_KIND: dict[TrackId, EstimateKind] = {
    TrackId.SYNTHETIC_REFERENCE_V021: EstimateKind.SIMULATION_SCORE,
    TrackId.REAL_PERSONAL_BASELINE_V1: EstimateKind.PERSONAL_OBSERVED_EPISODE_RATE,
    TrackId.REAL_LOGIT_CHALLENGER_V1: EstimateKind.SHADOW_CHALLENGER_SCORE,
}


class TargetDefinitionVersion(BlubathonModel):
    """The versioned question a real label answers.

    An imported intensity label proves a category exists in an export; it does
    not define how a new person should answer. Without an `active` version the
    system accepts demo fixtures and abstains from creating real labels
    .
    """

    target_definition_version: VersionLabel
    scope: TargetScope
    tenant_id: UUID | None = None
    question_es: SpanishText
    severity_anchors_es: tuple[SpanishText, ...] = Field(min_length=1)
    eligible_reporter_roles: frozenset[Role]
    eligible_source_mappings: frozenset[UUID] = frozenset()
    effective_from: UtcDatetime
    retired_at: UtcDatetime | None = None
    evidence_basis: SpanishText
    approval_status: ApprovalStatus
    clinical_review_id: UUID | None = None
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _scope_and_approval_agree(self) -> TargetDefinitionVersion:
        if self.scope is TargetScope.TENANT and self.tenant_id is None:
            raise ValueError("a tenant-scoped target definition needs tenant_id")
        if self.scope is TargetScope.DEMO_FIXTURE and self.tenant_id is not None:
            raise ValueError("a demo fixture target definition has no tenant")
        if not self.eligible_reporter_roles:
            raise ValueError("a target definition needs at least one eligible reporter role")
        if self.approval_status is ApprovalStatus.ACTIVE and self.clinical_review_id is None:
            raise ValueError("activation requires an accredited clinical review")
        return self

    @property
    def forces_synthetic_outcomes(self) -> bool:
        """Every outcome under a demo fixture target is synthetic."""

        return self.scope is TargetScope.DEMO_FIXTURE


class PredictionEpisode(BlubathonModel):
    """An immutable opportunity with a 24-hour window and a 48-hour deadline."""

    prediction_episode_id: UUID
    tenant_id: UUID
    subject_id: UUID
    form_session_id: UUID
    role: EpisodeRole = EpisodeRole.PRIMARY
    status: PredictionEpisodeStatus
    as_of_at: UtcDatetime
    prediction_at: UtcDatetime
    target_start_at: UtcDatetime
    target_end_at: UtcDatetime
    capture_deadline_at: UtcDatetime
    target_definition_version: VersionLabel
    care_mode: Tag
    profile_version: VersionLabel
    cohort_kind: CohortKind
    input_data_origin: DataOrigin
    feature_snapshot_id: UUID | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _window_is_exactly_the_spec_window(self) -> PredictionEpisode:
        if self.prediction_at != self.as_of_at:
            raise ValueError("prediction_at is as_of_at")
        if self.target_start_at != self.prediction_at:
            raise ValueError("target_start_at is prediction_at")
        if self.target_end_at != self.prediction_at + TARGET_HORIZON:
            raise ValueError("target_end_at is prediction_at plus the 24-hour horizon")
        if self.capture_deadline_at != self.prediction_at + CAPTURE_LIMIT:
            raise ValueError("capture_deadline_at is prediction_at plus the 48-hour limit")
        if (
            self.cohort_kind is CohortKind.DEMO_FIXTURE
            and self.input_data_origin is DataOrigin.REAL
        ):
            raise ValueError("a demo fixture episode never carries real input data")
        return self

    def contains(self, moment: UtcDatetime) -> bool:
        """The target window is open at the start and closed at the end."""

        return self.target_start_at < moment <= self.target_end_at


class FeatureSnapshot(BlubathonModel):
    """The closed instant a prediction was made from.

    It stores the exact projected IDs so it is never recomputed, and it refuses
    to mix origins: one synthetic row invalidates a real snapshot.
    """

    feature_snapshot_id: UUID
    tenant_id: UUID
    subject_id: UUID
    prediction_episode_id: UUID
    as_of_at: UtcDatetime
    input_data_origin: DataOrigin
    schema_version: VersionLabel
    projected_observation_ids: tuple[UUID, ...] = ()
    projected_outcome_resolution_ids: tuple[UUID, ...] = ()
    projected_consent_ids: tuple[UUID, ...] = ()
    observed_data_origins: frozenset[DataOrigin] = frozenset()
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _origins_never_mix(self) -> FeatureSnapshot:
        if self.input_data_origin not in self.observed_data_origins and self.observed_data_origins:
            raise ValueError("snapshot origin must appear among the observed origins")
        foreign = self.observed_data_origins - {self.input_data_origin}
        if foreign:
            raise ValueError(f"a {self.input_data_origin} snapshot rejects {sorted(foreign)} rows")
        return self


class PredictionOutput(BlubathonModel):
    """One track's answer for one episode, including its abstention."""

    prediction_output_id: UUID
    tenant_id: UUID
    prediction_episode_id: UUID
    track_id: TrackId
    intended_use: IntendedUse
    status: PredictionStatus
    estimate_kind: EstimateKind
    probability: Probability | None = None
    simulation_score: Probability | None = None
    shadow_score: Probability | None = None
    interval: Interval | None = None
    interval_method: IntervalMethod | None = None
    abstention_reasons: tuple[PredictionAbstentionReason, ...] = ()
    model_version: VersionLabel
    input_data_origin: DataOrigin
    created_at: UtcDatetime
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _track_semantics_hold(self) -> PredictionOutput:
        if self.intended_use is not TRACK_INTENDED_USE[self.track_id]:
            raise ValueError(f"{self.track_id} is a {TRACK_INTENDED_USE[self.track_id]} track")
        if self.estimate_kind is not TRACK_ESTIMATE_KIND[self.track_id]:
            raise ValueError(f"{self.track_id} reports {TRACK_ESTIMATE_KIND[self.track_id]}")
        if (
            self.track_id is TrackId.SYNTHETIC_REFERENCE_V021
            and self.input_data_origin is DataOrigin.REAL
        ):
            raise ValueError("the simulation track never runs on real input data")
        if (
            self.track_id is not TrackId.SYNTHETIC_REFERENCE_V021
            and self.input_data_origin is DataOrigin.SYNTHETIC
            and self.status is PredictionStatus.OK
        ):
            raise ValueError("a real track cannot report ok on synthetic input")

        if self.status is not PredictionStatus.OK:
            if not self.abstention_reasons:
                raise ValueError("an abstention states at least one reason")
            if any(
                value is not None
                for value in (
                    self.probability,
                    self.simulation_score,
                    self.shadow_score,
                    self.interval,
                    self.interval_method,
                )
            ):
                raise ValueError("an abstained output carries no number, interval or method")
            return self

        if self.abstention_reasons:
            raise ValueError("an ok output has no abstention reasons")

        if self.track_id is TrackId.REAL_PERSONAL_BASELINE_V1:
            if self.probability is None or self.interval is None or self.interval_method is None:
                raise ValueError("a visible real baseline needs probability, interval and method")
            if self.simulation_score is not None or self.shadow_score is not None:
                raise ValueError("a baseline reports a probability, not a score")
        elif self.track_id is TrackId.SYNTHETIC_REFERENCE_V021:
            if self.simulation_score is None:
                raise ValueError("a simulation reports simulation_score")
            if (
                self.probability is not None
                or self.interval is not None
                or self.interval_method is not None
                or self.shadow_score is not None
            ):
                raise ValueError("a simulation is never a clinical probability")
        else:
            # The challenger is operational now, so its number is a probability
            # like the baseline's: `shadow_score` was the field for a track that
            # nobody was allowed to read, and there is no such track any more.
            if self.probability is None:
                raise ValueError("an operational challenger reports a probability")
            if self.simulation_score is not None or self.shadow_score is not None:
                raise ValueError("a challenger reports a probability, not a score")
            # No interval: a logistic point estimate publishes no uncertainty of
            # its own, and borrowing the baseline's would misattribute it.
            if self.interval is not None or self.interval_method is not None:
                raise ValueError("the challenger publishes no interval")
        return self

    @property
    def is_exposable_to_caregiver(self) -> bool:
        """Whether this track's answer may reach a caregiver.

        It follows the declared intended use instead of naming a track: a
        simulation never reaches one, and both real tracks are operational
        support. Hard-coding the challenger here is what kept it hidden after it
        had stopped being a shadow model.
        """

        return self.intended_use is IntendedUse.OPERATIONAL_SUPPORT


class VoiEstimate(BlubathonModel):
    """Mutual information in nats, or an explicit reason it is unavailable.

    Unavailable means `voi_nats=null`. Zero would claim the value was computed
    and found uninformative.
    """

    field_code: FieldCode
    status: VoiStatus
    voi_nats: NonNegativeFloat | None = None
    q_estimator_version: VersionLabel | None = None
    conditional_model_version: VersionLabel | None = None
    cutoff_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _availability_matches_its_evidence(self) -> VoiEstimate:
        if self.status is VoiStatus.AVAILABLE:
            missing = [
                name
                for name, value in (
                    ("voi_nats", self.voi_nats),
                    ("q_estimator_version", self.q_estimator_version),
                    ("conditional_model_version", self.conditional_model_version),
                    ("cutoff_at", self.cutoff_at),
                )
                if value is None
            ]
            if missing:
                raise ValueError(f"an available VoI records {', '.join(missing)}")
        elif self.voi_nats is not None:
            raise ValueError("an unavailable VoI is null, never zero")
        return self


class TargetSelection(BlubathonModel):
    """The single selectable definition at a cutoff, or why there is none."""

    status: str
    target_definition_version: VersionLabel | None = None
    scope: TargetScope | None = None
    candidate_versions: tuple[VersionLabel, ...] = ()

    @model_validator(mode="after")
    def _status_is_one_of_three(self) -> TargetSelection:
        allowed = {"selected", "target_definition_unavailable", "target_definition_ambiguous"}
        if self.status not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        if self.status == "selected" and self.target_definition_version is None:
            raise ValueError("a selection names its version")
        if self.status != "selected" and self.target_definition_version is not None:
            raise ValueError("only a selection names a version")
        return self
