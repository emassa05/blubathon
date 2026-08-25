"""Request and response contracts for the eleven v0.3 routes (SPEC 11).

Every response has an explicit model; no route returns a bare dictionary. An
abstention is HTTP 200 with its own envelope, never the error envelope, and the
error envelope never carries clinical payload.
"""

from __future__ import annotations

from typing import Any, Literal, Self
from uuid import UUID

from pydantic import AnyUrl, Field, model_validator

from packages.shared.canonical import content_hash
from packages.shared.constants import API_PREFIX, CONTRACT_VERSION
from packages.shared.domain.base import (
    FaroModel,
    Interval,
    NonNegativeFloat,
    Probability,
    SpanishText,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.domain.evaluation import (
    AbstentionBreakdown,
    GroupMetric,
    MetricValue,
    SourceMetric,
)
from packages.shared.domain.observation import AnswerSubmission, DataQuality
from packages.shared.domain.prediction import TRACK_ESTIMATE_KIND, TRACK_INTENDED_USE
from packages.shared.enums import (
    DataOrigin,
    ErrorCode,
    EstimateKind,
    EvaluationReportStatus,
    ExecutionStatus,
    FieldCode,
    FormSessionKind,
    IntakeChannel,
    IntendedUse,
    IntervalMethod,
    OutcomeReportValue,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
    QuestionReason,
    RecommendationAbstentionReason,
    RecommendationItemType,
    RecommendationResponseStatus,
    ReviewDecision,
    ReviewStatus,
    Role,
    Source,
    SubmitStatus,
    TimingStatus,
    TrackId,
    VoiStatus,
)
from packages.shared.field_catalog import FieldValue, validate_field_value


class ErrorDetail(FaroModel):
    """Stable machine code plus sanitised Spanish copy (SPEC 11.7)."""

    code: ErrorCode
    message_es: SpanishText
    request_id: UUID


class ErrorResponse(FaroModel):
    error: ErrorDetail


class DefaultSuggestion(FaroModel):
    """A suggestion, not a value. The control stays empty until someone acts."""

    presentation_id: UUID
    value: FieldValue
    candidate_count: int = Field(ge=0)
    posterior_mean: Probability
    lower_bound: Probability
    n_observations: int = Field(ge=0)
    estimator_version: VersionLabel


class FormQuestion(FaroModel):
    """One field in the plan, with why it is there and what it may suggest."""

    field_code: FieldCode
    reason: QuestionReason
    voi_nats: NonNegativeFloat | None = None
    default: DefaultSuggestion | None = None

    @model_validator(mode="after")
    def _suggested_value_is_legal(self) -> Self:
        if self.default is not None:
            validate_field_value(self.field_code, self.default.value)
        return self


class FormSessionResponse(FaroModel):
    """The session envelope of SPEC 11.3, recalculated after every answer."""

    form_session_id: UUID
    subject_id: UUID
    source: Source
    session_kind: FormSessionKind
    opened_at: UtcDatetime
    audit_mode: bool
    form_policy_version: VersionLabel
    voi_status: VoiStatus
    highlighted: tuple[FormQuestion, ...] = ()
    tail: tuple[FormQuestion, ...] = ()
    data_quality: DataQuality | None = None

    @model_validator(mode="after")
    def _plan_keeps_every_applicable_field_once(self) -> Self:
        highlighted = [question.field_code for question in self.highlighted]
        tail = [question.field_code for question in self.tail]
        combined = highlighted + tail
        if len(set(combined)) != len(combined):
            raise ValueError("a field appears once, either highlighted or in the tail")
        if self.audit_mode and any(question.default is not None for question in self.highlighted):
            raise ValueError("an audited session returns no defaults")
        if self.audit_mode and any(question.default is not None for question in self.tail):
            raise ValueError("an audited session returns no defaults")
        return self


class FormSessionCreateRequest(FaroModel):
    """Audit mode, timestamps and policy version are the server's to decide."""

    subject_id: UUID
    source: Source
    session_kind: FormSessionKind


class FormAnswerRequest(FaroModel):
    """The client declares an interaction; the server derives the entry mode."""

    answer: AnswerSubmission


class FormSubmitResponse(FaroModel):
    """Only `episode_created` creates a snapshot, outputs and an outcome request."""

    form_session_id: UUID
    status: SubmitStatus
    submitted_at: UtcDatetime
    prediction_episode_id: UUID | None = None
    linked_prediction_episode_id: UUID | None = None

    @model_validator(mode="after")
    def _status_matches_its_references(self) -> Self:
        if self.status is SubmitStatus.EPISODE_CREATED:
            if self.prediction_episode_id is None:
                raise ValueError("episode_created names the episode it created")
            if self.linked_prediction_episode_id is not None:
                raise ValueError("episode_created does not also link")
        elif self.status is SubmitStatus.EPISODE_LINKED:
            if self.linked_prediction_episode_id is None:
                raise ValueError("episode_linked names the open episode it linked to")
            if self.prediction_episode_id is not None:
                raise ValueError("episode_linked creates nothing")
        else:
            if self.prediction_episode_id is not None:
                raise ValueError("no target definition means no episode is fabricated")
            if self.linked_prediction_episode_id is not None:
                raise ValueError("no target definition means nothing to link to")
        return self


class PredictionOutputView(FaroModel):
    """A single track's answer as a caller sees it (SPEC 11.5).

    `confidence` is absent on purpose. The shadow challenger never appears here.
    """

    track_id: TrackId
    intended_use: IntendedUse
    status: PredictionStatus
    estimate_kind: EstimateKind
    probability: Probability | None = None
    simulation_score: Probability | None = None
    interval: Interval | None = None
    interval_method: IntervalMethod | None = None
    abstention_reasons: tuple[PredictionAbstentionReason, ...] = ()
    model_version: VersionLabel
    input_data_origin: DataOrigin

    @model_validator(mode="after")
    def _track_semantics_hold_on_the_wire_too(self) -> Self:
        if self.track_id is TrackId.REAL_LOGIT_CHALLENGER_V1:
            raise ValueError("the shadow challenger is never exposed in v0.3")
        if self.intended_use is not TRACK_INTENDED_USE[self.track_id]:
            raise ValueError(f"{self.track_id} is a {TRACK_INTENDED_USE[self.track_id]} track")
        if self.estimate_kind is not TRACK_ESTIMATE_KIND[self.track_id]:
            raise ValueError(f"{self.track_id} reports {TRACK_ESTIMATE_KIND[self.track_id]}")
        if (
            self.track_id is TrackId.SYNTHETIC_REFERENCE_V021
            and self.input_data_origin is DataOrigin.REAL
        ):
            raise ValueError("the simulation track never runs on real input data")

        if self.status is not PredictionStatus.OK:
            if not self.abstention_reasons:
                raise ValueError("an abstention states at least one reason")
            if any(
                value is not None
                for value in (
                    self.probability,
                    self.simulation_score,
                    self.interval,
                    self.interval_method,
                )
            ):
                raise ValueError("an abstained output carries no number, interval or method")
            return self

        if self.abstention_reasons:
            raise ValueError("an ok output has no abstention reasons")
        if self.track_id is TrackId.SYNTHETIC_REFERENCE_V021:
            if self.simulation_score is None:
                raise ValueError("a simulation reports simulation_score")
            if (
                self.probability is not None
                or self.interval is not None
                or self.interval_method is not None
            ):
                raise ValueError("a simulation is never a clinical probability")
        elif self.probability is None or self.interval is None or self.interval_method is None:
            raise ValueError("a visible real baseline needs probability, interval and method")
        elif self.simulation_score is not None:
            raise ValueError("a baseline reports a probability, not a score")
        return self


class PredictionEpisodeResponse(FaroModel):
    """The authorised view of one episode: window, tracks and data quality."""

    prediction_episode_id: UUID
    subject_id: UUID
    as_of_at: UtcDatetime
    target_start_at: UtcDatetime
    target_end_at: UtcDatetime
    capture_deadline_at: UtcDatetime
    target_definition_version: VersionLabel
    outputs: tuple[PredictionOutputView, ...] = ()
    data_quality: DataQuality | None = None
    decision_policy_version: None = None
    risk_band: None = None


class OutcomeRequestView(FaroModel):
    """One pending item of the actor's inbox, with its derived state."""

    outcome_request_id: UUID
    prediction_episode_id: UUID
    subject_id: UUID
    target_definition_version: VersionLabel
    question_es: SpanishText
    severity_anchors_es: tuple[SpanishText, ...] = ()
    target_start_at: UtcDatetime
    target_end_at: UtcDatetime
    capture_deadline_at: UtcDatetime
    state: OutcomeRequestState
    resolution_status: OutcomeResolutionStatus


class OutcomeRequestListResponse(FaroModel):
    items: tuple[OutcomeRequestView, ...] = ()


class OutcomeReportRequest(FaroModel):
    """The client sends the answer only. Actor, role, timing and target are server-side."""

    value: OutcomeReportValue
    occurred_at: UtcDatetime | None = None
    supersedes_id: UUID | None = None

    @model_validator(mode="after")
    def _only_yes_states_when(self) -> Self:
        if self.value is OutcomeReportValue.YES:
            if self.occurred_at is None:
                raise ValueError("a yes report states when the event occurred")
        elif self.occurred_at is not None:
            raise ValueError("only a yes report carries occurred_at")
        return self


class OutcomeReportView(FaroModel):
    """The wire view refuses exactly what `OutcomeReport` refuses."""

    outcome_report_id: UUID
    prediction_episode_id: UUID
    value: OutcomeReportValue
    occurred_at: UtcDatetime | None = None
    reported_at: UtcDatetime
    timing_status: TimingStatus
    reporter_role: Role
    intake_channel: IntakeChannel
    target_definition_version: VersionLabel

    @model_validator(mode="after")
    def _only_yes_states_when(self) -> Self:
        if self.value is OutcomeReportValue.YES:
            if self.occurred_at is None:
                raise ValueError("a yes report states when the event occurred")
            if self.occurred_at > self.reported_at:
                raise ValueError("an event cannot occur after it was reported")
        elif self.occurred_at is not None:
            raise ValueError("only a yes report carries occurred_at")
        if self.timing_status is TimingStatus.MISSING:
            raise ValueError("missing describes an absent report, not a stored one")
        return self


class OutcomeResolutionView(FaroModel):
    """A resolution is not a report, and a conflict never becomes clean again."""

    status: OutcomeResolutionStatus
    resolved_at: UtcDatetime | None = None
    qualifying_report_id: UUID | None = None
    ever_conflicted: bool
    resolution_version: int = Field(ge=1)

    @model_validator(mode="after")
    def _status_carries_its_evidence(self) -> Self:
        conclusive = {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}
        if self.status in conclusive:
            if self.qualifying_report_id is None or self.resolved_at is None:
                raise ValueError("a conclusive resolution names its report and when it resolved")
        else:
            if self.qualifying_report_id is not None:
                raise ValueError("only a conclusive resolution has a qualifying report")
            if self.status is OutcomeResolutionStatus.PENDING and self.resolved_at is not None:
                raise ValueError("a pending resolution has no resolved_at")
        if self.status is OutcomeResolutionStatus.CONFLICTED and not self.ever_conflicted:
            raise ValueError("a conflicted resolution is by definition ever_conflicted")
        return self


class OutcomeReportResponse(FaroModel):
    """Report and resolution are returned separately; they are different facts."""

    report: OutcomeReportView
    resolution: OutcomeResolutionView


class CitationView(FaroModel):
    citation_id: UUID
    claim_id: UUID
    locator: str = Field(min_length=1)
    quoted_text: str = Field(min_length=1)
    canonical_url: AnyUrl


class StrategyItem(FaroModel):
    item_type: Literal[RecommendationItemType.STRATEGY] = RecommendationItemType.STRATEGY
    strategy_version_id: UUID
    review_status: ReviewStatus
    action_text_es: SpanishText
    citations: tuple[CitationView, ...] = ()


class HumanPlanItem(FaroModel):
    """A human plan never inherits the RAG citations (SPEC 10.2)."""

    item_type: Literal[RecommendationItemType.HUMAN_PLAN] = RecommendationItemType.HUMAN_PLAN
    human_plan_version_id: UUID
    action_text_es: SpanishText
    citations: tuple[CitationView, ...] = ()

    @model_validator(mode="after")
    def _carries_no_citations(self) -> Self:
        if self.citations:
            raise ValueError("a human plan shows no RAG citations")
        return self


RecommendationItem = StrategyItem | HumanPlanItem


class RecommendationResponse(FaroModel):
    """Matched, abstained, or waiting for a professional. Never a raw draft."""

    status: RecommendationResponseStatus
    recommendation_instance_id: UUID
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    items: tuple[RecommendationItem, ...] = ()
    reasons: tuple[RecommendationAbstentionReason, ...] = ()

    @model_validator(mode="after")
    def _status_matches_its_content(self) -> Self:
        if self.status is RecommendationResponseStatus.ABSTAINED:
            if self.items:
                raise ValueError("an abstained response carries no items")
            if not self.reasons:
                raise ValueError("an abstained response states its reason")
        elif self.status is RecommendationResponseStatus.AWAITING_PROFESSIONAL_REVIEW:
            if self.items:
                raise ValueError("nothing is exposed while every item is pending")
        elif not self.items:
            raise ValueError("a matched response carries the items it exposes")
        return self


class RecommendationInstanceView(FaroModel):
    """One row of the professional inbox, filtered in SQL by tenant and grant."""

    recommendation_instance_id: UUID
    prediction_episode_id: UUID
    subject_id: UUID
    scenario_hash: str = Field(min_length=1)
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    strategy_version_ids: tuple[UUID, ...] = ()
    review_status: ReviewStatus
    created_at: UtcDatetime


class RecommendationInboxResponse(FaroModel):
    items: tuple[RecommendationInstanceView, ...] = ()


class RecommendationReviewRequest(FaroModel):
    """One decision, one strategy version. Substitution carries its plan text."""

    strategy_version_id: UUID
    decision: ReviewDecision
    human_plan_action_text_es: SpanishText | None = None
    human_plan_allowed_executor_roles: frozenset[Role] | None = None

    @model_validator(mode="after")
    def _substitution_carries_its_plan(self) -> Self:
        substituting = self.decision is ReviewDecision.HUMAN_PLAN_SUBSTITUTED
        provided = (self.human_plan_action_text_es, self.human_plan_allowed_executor_roles)
        if substituting:
            if any(value is None for value in provided):
                raise ValueError("a substitution provides plan text and executor roles")
        elif any(value is not None for value in provided):
            raise ValueError("only a substitution provides a human plan")
        return self


class RecommendationReviewResponse(FaroModel):
    review_id: UUID
    recommendation_instance_id: UUID
    strategy_version_id: UUID
    decision: ReviewDecision
    reviewed_at: UtcDatetime
    human_plan_version_id: UUID | None = None


class StrategyExecutionRequest(FaroModel):
    """Applied, not applied or unknown, for exactly one strategy or plan."""

    strategy_version_id: UUID | None = None
    human_plan_version_id: UUID | None = None
    status: ExecutionStatus
    applied_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _references_exactly_one_item(self) -> Self:
        referenced = [self.strategy_version_id, self.human_plan_version_id]
        if sum(value is not None for value in referenced) != 1:
            raise ValueError("an execution references a strategy or a human plan, never both")
        if self.status is ExecutionStatus.APPLIED:
            if self.applied_at is None:
                raise ValueError("an applied execution states when it was applied")
        elif self.applied_at is not None:
            raise ValueError("only an applied execution carries applied_at")
        return self


class StrategyExecutionResponse(FaroModel):
    strategy_execution_id: UUID
    recommendation_instance_id: UUID
    status: ExecutionStatus
    recorded_at: UtcDatetime
    applied_at: UtcDatetime | None = None


class EvaluationResponse(FaroModel):
    """Every report says which data it came from and what it cannot show."""

    model_version: VersionLabel
    track_id: TrackId
    status: EvaluationReportStatus
    data_origin: DataOrigin
    intended_use: IntendedUse
    dataset_sha256: str = Field(min_length=1)
    target_definition_version: VersionLabel
    protocol_version: VersionLabel
    metrics: tuple[MetricValue, ...] = ()
    group_metrics: tuple[GroupMetric, ...] = ()
    source_metrics: tuple[SourceMetric, ...] = ()
    decision_coverage: MetricValue | None = None
    abstentions: tuple[AbstentionBreakdown, ...] = ()
    limitations_es: tuple[str, ...] = Field(min_length=1)


class IdempotencyScope(FaroModel):
    """`(tenant, actor, method, concrete path, key)` (SPEC 11.2).

    The concrete path includes every normalised ID, so the same key on two
    different resources can never replay one another's response.
    """

    tenant_id: UUID
    actor_id: UUID
    method: str
    normalized_concrete_path: str
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def _path_is_concrete(self) -> Self:
        if "{" in self.normalized_concrete_path or "}" in self.normalized_concrete_path:
            raise ValueError("the scope uses the concrete path, not the route template")
        if not self.normalized_concrete_path.startswith(API_PREFIX):
            raise ValueError(f"a concrete path starts with {API_PREFIX}")
        return self

    def fingerprint(self) -> str:
        return content_hash("idempotency_scope", CONTRACT_VERSION, self.canonical_payload())


def request_fingerprint(
    scope: IdempotencyScope,
    *,
    path_params: dict[str, Any],
    query: dict[str, Any],
    body: Any,
) -> str:
    """Hash of scope, path params, canonical query and body (SPEC 11.2)."""

    payload = {
        "scope": scope.canonical_payload(),
        "path_params": path_params,
        "query": query,
        "body": body,
    }
    return content_hash("idempotency_request", CONTRACT_VERSION, payload)
