"""Modelos de request y response de la API v0.3.

PROVISIONAL - PUERTO HACIA P1 (ver ``apps/api/contracts/__init__.py``).

`CONVENTIONS 6` sitúa estos modelos en `packages/shared`, propiedad de P1. Se
declaran aquí para poder construir rutas, servicios y UI antes de H1. Todos usan
`extra="forbid"`, UUID v4 y timestamps UTC conscientes de zona, y ninguno
sustituye un contrato con `dict[str, object]`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import UUID4, BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

from apps.api.canonical import format_timestamp, parse_timestamp
from apps.api.contracts.enums import (
    AnswerInteraction,
    CatalogAvailability,
    EntryMode,
    ExecutionStatus,
    ItemType,
    OutcomeRequestStatus,
    OutcomeValue,
    PredictionStatus,
    RecommendationResponseStatus,
    ResolutionStatus,
    ReviewDecision,
    Role,
    RuntimeStatus,
    SessionKind,
    Source,
    TimingStatus,
    VoiStatus,
)


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return parse_timestamp(value)
    raise ValueError("se esperaba un timestamp ISO-8601 UTC")


UtcTimestamp = Annotated[
    datetime,
    BeforeValidator(_timestamp),
    PlainSerializer(format_timestamp, return_type=str),
]
Uuid = Annotated[UUID4, PlainSerializer(str, return_type=str)]


class FaroModel(BaseModel):
    """Frontera de API: nada implícito entra ni sale."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True, frozen=True)


# -- errores -------------------------------------------------------------


class ErrorBody(FaroModel):
    code: str
    message_es: str
    request_id: str


class ErrorEnvelope(FaroModel):
    error: ErrorBody


# -- formulario ----------------------------------------------------------


class OpenFormSessionRequest(FaroModel):
    subject_id: Uuid
    source: Source
    session_kind: SessionKind = SessionKind.CAREGIVER_DAILY


class DefaultSuggestion(FaroModel):
    """SPEC 11.3. Ayuda, nunca valor del control (CONVENTIONS 10)."""

    presentation_id: Uuid
    value: Any
    candidate_count: int
    posterior_mean: float
    lower_bound: float
    n_observations: int
    estimator_version: str


class PlannedQuestionView(FaroModel):
    field_code: str
    reason: str
    voi_nats: float | None = None
    default: DefaultSuggestion | None = None


class OutcomePendingBlock(FaroModel):
    """SPEC 6.9: bloque aparte que no consume cupos de campos diarios."""

    prediction_episode_id: Uuid
    question_es: str
    severity_anchors_es: list[str]
    target_end_at: UtcTimestamp
    capture_deadline_at: UtcTimestamp
    status: OutcomeRequestStatus


class FormSessionView(FaroModel):
    form_session_id: Uuid
    subject_id: Uuid
    source: Source
    session_kind: SessionKind
    status: str
    opened_at: UtcTimestamp
    submitted_at: UtcTimestamp | None = None
    audit_mode: bool
    form_policy_version: str
    voi_status: VoiStatus
    plan_source: str
    outcome_pending: OutcomePendingBlock | None = None
    highlighted: list[PlannedQuestionView]
    tail: list[PlannedQuestionView]
    answered_field_codes: list[str]
    emergency_notice_es: str


class AnswerRequest(FaroModel):
    """El cliente declara interacción; el servidor deriva `entry_mode`."""

    field_code: str
    interaction: AnswerInteraction
    value: Any | None = None
    default_presentation_id: Uuid | None = None
    effective_at: UtcTimestamp | None = None
    supersedes_id: Uuid | None = None


class AnswerAcceptedView(FaroModel):
    field_observation_id: Uuid | None
    field_code: str
    entry_mode: EntryMode
    session: FormSessionView


class SubmitFormSessionRequest(FaroModel):
    """El cierre no lleva payload: el servidor fija `submitted_at`."""


class SubmitFormSessionView(FaroModel):
    form_session_id: Uuid
    status: PredictionStatus
    submitted_at: UtcTimestamp
    prediction_episode_id: Uuid | None = None
    linked_prediction_episode_id: Uuid | None = None
    outcome_request_id: Uuid | None = None
    recommendation_instance_id: Uuid | None = None
    reasons: list[str] = Field(default_factory=list)
    emergency_notice_es: str


# -- predicción ----------------------------------------------------------


class PredictionOutputView(FaroModel):
    """SPEC 11.5. Sin `confidence`: no tiene semántica única entre tracks."""

    track_id: str
    intended_use: str
    status: str
    estimate_kind: str
    probability: float | None = None
    simulation_score: float | None = None
    interval: tuple[float, float] | None = None
    interval_method: str | None = None
    abstention_reasons: list[str]
    model_version: str
    input_data_origin: str
    decision_policy_version: None = None
    risk_band: None = None


class PredictionEpisodeView(FaroModel):
    prediction_episode_id: Uuid
    subject_id: Uuid
    as_of_at: UtcTimestamp
    prediction_at: UtcTimestamp
    target_start_at: UtcTimestamp
    target_end_at: UtcTimestamp
    capture_deadline_at: UtcTimestamp
    target_definition_version: str
    outputs: list[PredictionOutputView]
    outcome_status: OutcomeRequestStatus | None = None
    resolution_status: ResolutionStatus | None = None
    emergency_notice_es: str


# -- outcome -------------------------------------------------------------


class OutcomeRequestView(FaroModel):
    outcome_request_id: Uuid
    prediction_episode_id: Uuid
    subject_id: Uuid
    subject_label: str
    question_es: str
    severity_anchors_es: list[str]
    target_start_at: UtcTimestamp
    target_end_at: UtcTimestamp
    capture_deadline_at: UtcTimestamp
    status: OutcomeRequestStatus
    resolution_status: ResolutionStatus


class OutcomeRequestListView(FaroModel):
    items: list[OutcomeRequestView]
    emergency_notice_es: str


class CreateOutcomeReportRequest(FaroModel):
    value: OutcomeValue
    occurred_at: UtcTimestamp | None = None
    supersedes_id: Uuid | None = None


class OutcomeReportView(FaroModel):
    outcome_report_id: Uuid
    prediction_episode_id: Uuid
    value: OutcomeValue
    occurred_at: UtcTimestamp | None
    reported_at: UtcTimestamp
    timing_status: TimingStatus
    reporter_role: Role
    target_definition_version: str
    supersedes_id: Uuid | None = None


class OutcomeResolutionView(FaroModel):
    outcome_resolution_id: Uuid
    status: ResolutionStatus
    resolved_at: UtcTimestamp | None
    qualifying_report_id: Uuid | None
    ever_conflicted: bool
    resolution_version: int


class OutcomeReportResponse(FaroModel):
    """SPEC 11.4: reporte y resolución van por separado."""

    report: OutcomeReportView
    resolution: OutcomeResolutionView
    request_status: OutcomeRequestStatus


# -- recomendación -------------------------------------------------------


class CitationView(FaroModel):
    citation_id: Uuid
    claim_id: str
    locator: str
    quoted_text: str
    canonical_url: str


class RecommendationItemView(FaroModel):
    item_type: ItemType
    review_status: str
    strategy_version_id: Uuid | None = None
    human_plan_version_id: Uuid | None = None
    action_text_es: str
    required_approver_role: Role | None = None
    allowed_executor_roles: list[Role] = Field(default_factory=list)
    citations: list[CitationView] = Field(default_factory=list)
    non_actionable: str | None = None
    execution_status: ExecutionStatus | None = None


class RecommendationsView(FaroModel):
    status: RecommendationResponseStatus
    recommendation_instance_id: Uuid
    catalog_version: str | None = None
    corpus_version: str | None = None
    availability_reason: CatalogAvailability
    reasons: list[str] = Field(default_factory=list)
    items: list[RecommendationItemView] = Field(default_factory=list)
    revision: str
    emergency_notice_es: str


class ScenarioView(FaroModel):
    """SPEC 9.7: sin identidad, notas, IDs externos ni historial."""

    schema_version: str
    field_values: dict[str, str]
    context_tags: list[str]
    profile_tags: list[str]
    contraindication_tags: list[str]


class RecommendationInstanceSummary(FaroModel):
    recommendation_instance_id: Uuid
    prediction_episode_id: Uuid
    subject_id: Uuid
    subject_label: str
    created_at: UtcTimestamp
    catalog_version: str | None
    corpus_version: str | None
    runtime_status: RuntimeStatus
    scenario: ScenarioView | None
    pending_strategy_version_ids: list[Uuid]
    revision: str


class RecommendationInboxView(FaroModel):
    items: list[RecommendationInstanceSummary]
    emergency_notice_es: str


class HumanPlanInput(FaroModel):
    action_text_es: str = Field(min_length=1, max_length=2000)
    allowed_executor_roles: list[Role] = Field(min_length=1)


class CreateReviewRequest(FaroModel):
    strategy_version_id: Uuid
    decision: ReviewDecision
    human_plan: HumanPlanInput | None = None
    supersedes_id: Uuid | None = None


class ReviewView(FaroModel):
    review_id: Uuid
    recommendation_instance_id: Uuid
    strategy_version_id: Uuid
    decision: ReviewDecision
    reviewed_by: Uuid
    reviewer_role: Role
    reviewed_at: UtcTimestamp
    human_plan_version_id: Uuid | None = None
    supersedes_id: Uuid | None = None
    revision: str


class CreateExecutionRequest(FaroModel):
    status: ExecutionStatus
    strategy_version_id: Uuid | None = None
    human_plan_version_id: Uuid | None = None
    applied_at: UtcTimestamp | None = None
    supersedes_id: Uuid | None = None


class ExecutionView(FaroModel):
    strategy_execution_id: Uuid
    recommendation_instance_id: Uuid
    strategy_version_id: Uuid | None
    human_plan_version_id: Uuid | None
    status: ExecutionStatus
    actor_id: Uuid
    actor_role: Role
    recorded_at: UtcTimestamp
    applied_at: UtcTimestamp | None
    exposure_eligible: bool
    revision: str


# -- evaluación ----------------------------------------------------------


class MetricView(FaroModel):
    name: str
    estimability: Literal["estimable", "not_estimable"]
    value: float | None = None
    interval: tuple[float, float] | None = None
    reason: str | None = None


class EvaluationReportView(FaroModel):
    model_config = ConfigDict(
        extra="forbid", use_enum_values=True, frozen=True, protected_namespaces=()
    )

    evaluation_report_id: Uuid
    model_version: str
    track_id: str
    model_state: str
    intended_use: str
    data_origin: str
    dataset_sha256: str
    target_definition_version: str | None
    protocol_version: str
    metrics: list[MetricView]
    abstention_by_reason: dict[str, float]
    limitations_es: list[str]
    published_at: UtcTimestamp | None
    simulation_only: bool


# -- sujetos (soporte de UI) ---------------------------------------------


class SubjectView(FaroModel):
    subject_id: Uuid
    display_label: str
    cohort_kind: str


class SessionContextView(FaroModel):
    actor_id: Uuid
    display_name: str
    tenant_id: Uuid
    roles: list[Role]
    subjects: list[SubjectView]
    deployment_mode: str
    adapters_source: str
    emergency_notice_es: str


def uuid_or_none(value: UUID | str | None) -> str | None:
    return None if value is None else str(value)
