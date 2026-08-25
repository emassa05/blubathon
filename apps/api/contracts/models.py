"""Contrato de request y response de la API v0.3.

Los modelos del contrato viven en `packages/shared/domain/**` y H1 los publicó.
Este módulo los reexporta y **no vuelve a declarar ninguno**: tipos, rangos y
validadores llegan desde P1, así que las reglas de `SPEC 8.5`, `SPEC 10.2` y
`SPEC 11.5` las hace cumplir el contrato y no una copia paralela.

Cinco respuestas de producto necesitan campos que el contrato publicado todavía
no tiene. Se declaran aquí **como subclase del modelo de P1**, nunca como copia:
lo único declarado es lo que falta, cada añadido lleva su solicitud, y las
solicitudes están en "Solicitudes a P1" del `README.md` con ruta, request,
response, razón y test consumidor.
"""

from __future__ import annotations

from uuid import UUID

from packages.shared.domain.api import (
    CitationView,
    DefaultSuggestion,
    ErrorDetail,
    ErrorResponse,
    EvaluationResponse,
    FormAnswerRequest,
    FormQuestion,
    FormSessionCreateRequest,
    FormSessionResponse,
    FormSubmitResponse,
    HumanPlanItem,
    IdempotencyScope,
    OutcomeReportRequest,
    OutcomeReportResponse,
    OutcomeReportView,
    OutcomeRequestListResponse,
    OutcomeRequestView,
    OutcomeResolutionView,
    PredictionEpisodeResponse,
    PredictionOutputView,
    RecommendationInboxResponse,
    RecommendationInstanceView,
    RecommendationItem,
    RecommendationResponse,
    RecommendationReviewRequest,
    RecommendationReviewResponse,
    StrategyExecutionRequest,
    StrategyExecutionResponse,
    StrategyItem,
    request_fingerprint,
)
from packages.shared.domain.base import FaroModel, Interval, SpanishText, UtcDatetime
from packages.shared.domain.evaluation import AbstentionBreakdown, MetricValue
from packages.shared.domain.observation import AnswerSubmission, DataQuality
from packages.shared.domain.rag import ScenarioV1
from packages.shared.enums import (
    CohortKind,
    DeploymentMode,
    EntryMode,
    EvaluationReportStatus,
    ExecutionStatus,
    FieldCode,
    FormSessionStatus,
    ModelState,
    NonActionableReason,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    Role,
    RuntimeStatus,
)

# -- envoltorio de producto sobre el contrato publicado -------------------


class AnswerSubmissionView(AnswerSubmission):
    """`AnswerSubmission` de P1 más lo que una corrección necesita.

    Solicitud R12: `SPEC 5.8` hace append-only la observación diaria y una
    corrección se enlaza con `supersedes_id`; `SPEC 5.5` permite declarar el
    instante efectivo de lo observado. El contrato publicado no lleva ninguno de
    los dos, así que una corrección no se puede expresar.
    """

    effective_at: UtcDatetime | None = None
    supersedes_id: UUID | None = None


class AnswerRequest(FormAnswerRequest):
    """`FormAnswerRequest` de P1 con el envío extendido de la solicitud R12."""

    answer: AnswerSubmissionView


class OutcomePendingBlock(FaroModel):
    """Bloque de outcome pendiente del formulario (`SPEC 6.9`, paso 1).

    Solicitud R5: `FormSessionResponse` no publica el bloque. `FormPlan` de P1
    lo reduce a `outcome_pending: bool`, así que la pregunta, sus anclas y sus
    plazos no llegan al cliente por el contrato.
    """

    prediction_episode_id: UUID
    question_es: SpanishText
    severity_anchors_es: tuple[SpanishText, ...] = ()
    target_end_at: UtcDatetime
    capture_deadline_at: UtcDatetime
    state: OutcomeRequestState


class FormSessionView(FormSessionResponse):
    """`FormSessionResponse` de P1 más lo que la pantalla del cuidador necesita.

    Solicitud R5: bloque de outcome pendiente, estado de la sesión, campos ya
    respondidos y origen del plan. Ninguno existe en el contrato publicado.
    """

    status: FormSessionStatus
    submitted_at: UtcDatetime | None = None
    plan_source: str
    outcome_pending: OutcomePendingBlock | None = None
    answered_field_codes: tuple[FieldCode, ...] = ()


class AnswerAcceptedView(FaroModel):
    """Respuesta de `POST /form-sessions/{id}/answers`.

    Solicitud R9: el contrato publica el request (`FormAnswerRequest`) pero no
    la respuesta. El cliente necesita saber qué observación se creó y con qué
    `entry_mode` la derivó el servidor (`SPEC 5.5`), además del plan recalculado.
    """

    field_observation_id: UUID | None = None
    field_code: FieldCode
    entry_mode: EntryMode
    session: FormSessionView


class SubmitFormSessionView(FormSubmitResponse):
    """`FormSubmitResponse` de P1 más las referencias que el cierre creó.

    Solicitud R1: `SubmitStatus` no distingue "no hay definición" de "hay más de
    una" y la respuesta no lleva razones, así que la causa del cierre fallido no
    llega al cliente. `reasons` la transporta mientras P1 decide.
    """

    outcome_request_id: UUID | None = None
    recommendation_instance_id: UUID | None = None
    reasons: tuple[PredictionAbstentionReason, ...] = ()


class PredictionEpisodeView(PredictionEpisodeResponse):
    """`PredictionEpisodeResponse` de P1 más el estado del outcome.

    Solicitud R10: la pantalla del cuidador muestra si la ventana sigue abierta
    sin pedir otra ruta. `prediction_at` es el instante en que se calcularon las
    salidas, distinto del cutoff `as_of_at` (`SPEC 4.1`).
    """

    prediction_at: UtcDatetime
    outcome_state: OutcomeRequestState | None = None
    resolution_status: OutcomeResolutionStatus | None = None


class StrategyItemView(StrategyItem):
    """`StrategyItem` de P1 más lo que hace accionable a la estrategia.

    Solicitud R8: sin `required_approver_role` y `allowed_executor_roles` el
    cliente no sabe quién puede aprobar ni quién puede aplicar; sin
    `non_actionable` no puede mostrar que una dependencia suspendida bloquea
    nuevas acciones (`SPEC 10.2`); sin `execution_status` no sabe si ya se
    registró una aplicación (`SPEC 10.3`).
    """

    required_approver_role: Role | None = None
    allowed_executor_roles: tuple[Role, ...] = ()
    non_actionable: NonActionableReason | None = None
    execution_status: ExecutionStatus | None = None


class HumanPlanItemView(HumanPlanItem):
    """`HumanPlanItem` de P1 con los mismos añadidos de la solicitud R8.

    `strategy_version_id` solo viaja hacia un profesional: es la estrategia que
    el plan humano sustituyó, y la familia no necesita verla (`SPEC 10.2`).
    """

    strategy_version_id: UUID | None = None
    required_approver_role: Role | None = None
    allowed_executor_roles: tuple[Role, ...] = ()
    non_actionable: NonActionableReason | None = None
    execution_status: ExecutionStatus | None = None


RecommendationItemView = StrategyItemView | HumanPlanItemView


class RecommendationsView(RecommendationResponse):
    """`RecommendationResponse` de P1 más el token de concurrencia.

    Solicitud R13: `SPEC 11.2` exige `If-Match` sobre los recursos con revisión,
    y el contrato publicado no lleva ningún token que el cliente pueda devolver.
    `revision` viaja además en la cabecera `ETag` de la lectura individual.

    `items` cambia de tipo al de la solicitud R8; los estados, las versiones y
    los validadores siguen siendo los de P1.
    """

    items: tuple[RecommendationItemView, ...] = ()
    revision: str


class RecommendationInstanceSummary(RecommendationInstanceView):
    """`RecommendationInstanceView` de P1 más lo que el inbox profesional usa.

    Solicitud R7: el contrato publica `scenario_hash`, que identifica el
    escenario pero no lo describe. Quien revisa necesita ver el escenario mínimo
    (`SPEC 9.7`, sin identificadores directos) para juzgar aplicabilidad, saber
    qué estrategias siguen pendientes y de quién es el registro.
    """

    subject_label: SpanishText
    runtime_status: RuntimeStatus
    scenario: ScenarioV1 | None = None
    pending_strategy_version_ids: tuple[UUID, ...] = ()
    revision: str


class RecommendationInboxView(RecommendationInboxResponse):
    """`RecommendationInboxResponse` con los resúmenes de la solicitud R7."""

    items: tuple[RecommendationInstanceSummary, ...] = ()


class OutcomeReportResponseView(OutcomeReportResponse):
    """`OutcomeReportResponse` de P1 más el estado derivado de la solicitud.

    Solicitud R14: `SPEC 4.4` deriva el estado de la `OutcomeRequest` del reloj
    y de la resolución activa. P1 publica la regla (`derive_request_state`) pero
    la respuesta al reportar no la devuelve, y el cliente no puede derivarla sin
    reimplementar la precedencia.
    """

    request_state: OutcomeRequestState


class ExecutionView(StrategyExecutionResponse):
    """`StrategyExecutionResponse` de P1 más qué se aplicó y si cuenta.

    Solicitud R15: la respuesta publicada no dice qué estrategia o plan se
    aplicó, y `SPEC 10.3` distingue una aplicación tardía, que se conserva pero
    no se atribuye. P1 publica la regla (`exposure_is_eligible`) pero no un
    campo donde devolver su resultado.
    """

    strategy_version_id: UUID | None = None
    human_plan_version_id: UUID | None = None
    exposure_eligible: bool


class EvaluationReportView(EvaluationResponse):
    """`EvaluationResponse` de P1 más la identidad de la fila publicada.

    Solicitud R11: el reporte servido no dice qué fila es
    (`evaluation_report_id`), en qué estado está el modelo (`ModelState`,
    `SPEC 14.2`) ni cuándo se publicó.
    """

    model_config = EvaluationResponse.model_config | {"protected_namespaces": ()}

    evaluation_report_id: UUID
    model_state: ModelState
    published_at: UtcDatetime | None = None


# -- rutas de soporte, fuera de `SPEC 11.1` -------------------------------


class SubjectView(FaroModel):
    """Sujeto con etiqueta visible. Ruta de soporte, no del contrato."""

    subject_id: UUID
    display_label: SpanishText
    cohort_kind: CohortKind


class SessionContextView(FaroModel):
    """`GET /session`: quién soy y sobre qué sujetos tengo grant.

    No es una ruta de `SPEC 11.1` y P1 no publica un modelo para ella. No
    devuelve ningún dato clínico.
    """

    actor_id: UUID
    display_name: SpanishText
    tenant_id: UUID
    roles: tuple[Role, ...] = ()
    subjects: tuple[SubjectView, ...] = ()
    deployment_mode: DeploymentMode
    adapters_source: str


def uuid_or_none(value: UUID | str | None) -> str | None:
    return None if value is None else str(value)


__all__ = [
    "AbstentionBreakdown",
    "AnswerAcceptedView",
    "AnswerRequest",
    "AnswerSubmission",
    "AnswerSubmissionView",
    "CitationView",
    "DataQuality",
    "DefaultSuggestion",
    "ErrorDetail",
    "ErrorResponse",
    "EvaluationReportStatus",
    "EvaluationReportView",
    "EvaluationResponse",
    "ExecutionStatus",
    "ExecutionView",
    "FaroModel",
    "FormAnswerRequest",
    "FormQuestion",
    "FormSessionCreateRequest",
    "FormSessionResponse",
    "FormSessionView",
    "FormSubmitResponse",
    "HumanPlanItem",
    "HumanPlanItemView",
    "IdempotencyScope",
    "Interval",
    "MetricValue",
    "OutcomePendingBlock",
    "OutcomeReportRequest",
    "OutcomeReportResponse",
    "OutcomeReportResponseView",
    "OutcomeReportView",
    "OutcomeRequestListResponse",
    "OutcomeRequestView",
    "OutcomeResolutionView",
    "PredictionEpisodeResponse",
    "PredictionEpisodeView",
    "PredictionOutputView",
    "RecommendationInboxResponse",
    "RecommendationInboxView",
    "RecommendationInstanceSummary",
    "RecommendationInstanceView",
    "RecommendationItem",
    "RecommendationItemView",
    "RecommendationResponse",
    "RecommendationReviewRequest",
    "RecommendationReviewResponse",
    "RecommendationsView",
    "ScenarioV1",
    "SessionContextView",
    "StrategyExecutionRequest",
    "StrategyExecutionResponse",
    "StrategyItem",
    "StrategyItemView",
    "SubjectView",
    "SubmitFormSessionView",
    "request_fingerprint",
    "uuid_or_none",
]
