"""Blubathon v0.4 HTTP and WebSocket surface."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query, WebSocket, WebSocketDisconnect

from apps.api.canonical import parse_timestamp
from apps.api.contracts.constants import API_PREFIX
from apps.api.contracts.models import (
    AnswerItem,
    CalibrationResponse,
    ChildHistoryResponse,
    ChildListResponse,
    ChildView,
    FeedbackRequest,
    FeedbackResponse,
    FormPlanRequest,
    FormPlanResponse,
    FormSubmissionRequest,
    FormSubmissionResponse,
    OutcomeReportRequest,
    OutcomeReportResponseView,
    OutcomeRequestListResponse,
    PredictionEpisodeView,
    RecommendationDecisionRequest,
    RecommendationDecisionResponse,
    RecommendationInstanceView,
    RecommendationListResponse,
    ReviewQueueResponse,
    TodayRecommendationResponse,
)
from apps.api.events import EventBroker
from apps.api.routes.dependencies import Broker, Context, Registry
from apps.api.services import ServiceRegistry
from apps.api.services.local_time import local_date as reference_date

router = APIRouter(prefix=API_PREFIX)


@router.get("/children", response_model=ChildListResponse)
def list_children(context: Context, services: Registry) -> ChildListResponse:
    with services.core.database.read() as connection:
        return services.children.list(connection, tenant_id=context.tenant_id)


@router.get("/children/{child_id}", response_model=ChildView)
def read_child(child_id: str, context: Context, services: Registry) -> ChildView:
    now = services.core.now()
    with services.core.database.read() as connection:
        return services.children.get(
            connection, tenant_id=context.tenant_id, child_id=child_id, now=now
        )


@router.get("/calibration", response_model=CalibrationResponse)
def cohort_calibration(context: Context, services: Registry) -> CalibrationResponse:
    """Si lo que se anuncia acaba pasando, medido sobre toda la organización.

    Sin `child_id` y a propósito: comprobar una frecuencia con ±10 puntos pide
    del orden de cien días **en cada tramo**, y una sola persona tarda años en
    repartirlos. Esto responde si el modelo acierta, no si acierta con alguien.
    """

    with services.core.database.read() as connection:
        return services.calibration.cohort(connection, tenant_id=context.tenant_id)


@router.get("/children/{child_id}/history", response_model=ChildHistoryResponse)
def child_history(
    child_id: str,
    context: Context,
    services: Registry,
    limit: int = Query(default=30, ge=1, le=100),
) -> ChildHistoryResponse:
    with services.core.database.read() as connection:
        return services.children.history(
            connection, tenant_id=context.tenant_id, child_id=child_id, limit=limit
        )


@router.get(
    "/children/{child_id}/recommendations/today",
    response_model=TodayRecommendationResponse,
)
def today_recommendation(
    child_id: str, context: Context, services: Registry
) -> TodayRecommendationResponse:
    now = services.core.now()
    local_date = reference_date(parse_timestamp(now)).isoformat()
    with services.core.database.read() as connection:
        return services.recommendations.today(
            connection,
            tenant_id=context.tenant_id,
            child_id=child_id,
            local_date=local_date,
        )


@router.post("/children/{child_id}/form-plan", response_model=FormPlanResponse)
def form_plan(
    child_id: str,
    payload: FormPlanRequest,
    context: Context,
    services: Registry,
) -> FormPlanResponse:
    return services.submissions.build_plan(
        tenant_id=context.tenant_id,
        subject_id=child_id,
        source=payload.source,
        answers=payload.answers,
        now=services.core.now(),
    )


@router.post("/children/{child_id}/forms", status_code=201, response_model=FormSubmissionResponse)
def submit_form(
    child_id: str,
    payload: FormSubmissionRequest,
    background_tasks: BackgroundTasks,
    context: Context,
    services: Registry,
    broker: Broker,
) -> FormSubmissionResponse:
    now = services.core.now()
    with services.core.database.write() as connection:
        result = services.submissions.submit(
            connection,
            tenant_id=context.tenant_id,
            subject_id=child_id,
            source=payload.source,
            local_date=payload.local_date.isoformat(),
            answers=payload.answers,
            now=now,
        )
    if result.recommendation_instance_id is not None:
        background_tasks.add_task(
            _generate_recommendation,
            services,
            broker,
            context.tenant_id,
            child_id,
            str(result.prediction_episode_id),
            payload.answers,
        )
    return result


@router.get("/prediction-episodes/{prediction_episode_id}", response_model=PredictionEpisodeView)
def read_prediction_episode(
    prediction_episode_id: str, context: Context, services: Registry
) -> PredictionEpisodeView:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.episodes.get(
            connection,
            tenant_id=context.tenant_id,
            prediction_episode_id=prediction_episode_id,
            now=now,
        )


@router.get("/outcome-requests", response_model=OutcomeRequestListResponse)
def list_outcome_requests(context: Context, services: Registry) -> OutcomeRequestListResponse:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.outcomes.list_requests(connection, tenant_id=context.tenant_id, now=now)


@router.post(
    "/prediction-episodes/{prediction_episode_id}/outcome-reports",
    status_code=201,
    response_model=OutcomeReportResponseView,
)
def create_outcome_report(
    prediction_episode_id: str,
    payload: OutcomeReportRequest,
    context: Context,
    services: Registry,
) -> OutcomeReportResponseView:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.outcomes.create_report(
            connection,
            tenant_id=context.tenant_id,
            prediction_episode_id=prediction_episode_id,
            request=payload,
            now=now,
        )


@router.get(
    "/prediction-episodes/{prediction_episode_id}/recommendations",
    response_model=RecommendationInstanceView,
)
def episode_recommendation(
    prediction_episode_id: str, context: Context, services: Registry
) -> RecommendationInstanceView:
    with services.core.database.read() as connection:
        return services.recommendations.for_episode(
            connection,
            tenant_id=context.tenant_id,
            prediction_episode_id=prediction_episode_id,
        )


@router.get("/recommendations", response_model=RecommendationListResponse)
def list_recommendations(
    context: Context,
    services: Registry,
    status: Literal["pending", "matched", "abstained"] | None = None,
    child_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> RecommendationListResponse:
    with services.core.database.read() as connection:
        return services.recommendations.list(
            connection,
            tenant_id=context.tenant_id,
            status=status,
            child_id=child_id,
            limit=limit,
        )


@router.get("/recommendations/review-queue", response_model=ReviewQueueResponse)
def review_queue(
    context: Context,
    services: Registry,
    limit: int = Query(default=20, ge=1, le=100),
) -> ReviewQueueResponse:
    """La muestra de recomendaciones que el profesional tiene que revisar.

    Va **antes** de `/recommendations/{id}/feedback` en este archivo por una
    razón mecánica: FastAPI resuelve por orden de declaración y
    `/recommendations/review-queue` casaría con cualquier ruta
    `/recommendations/{algo}` declarada antes que ella.
    """

    with services.core.database.read() as connection:
        return services.recommendations.review_queue(
            connection, tenant_id=context.tenant_id, limit=limit
        )


@router.post(
    "/recommendations/{recommendation_instance_id}/review",
    status_code=201,
    response_model=RecommendationDecisionResponse,
)
def create_review(
    recommendation_instance_id: str,
    payload: RecommendationDecisionRequest,
    context: Context,
    services: Registry,
    broker: Broker,
) -> RecommendationDecisionResponse:
    now = services.core.now()
    with services.core.database.write() as connection:
        result = services.recommendations.review(
            connection,
            tenant_id=context.tenant_id,
            recommendation_instance_id=recommendation_instance_id,
            request=payload,
            now=now,
        )
    # Sin tarea de fondo: un rechazo no redacta de nuevo. El evento existe para
    # que una pantalla abierta en otra pestaña vea salir el elemento de la cola.
    broker.publish(
        {
            "type": "review.recorded",
            "recommendation_instance_id": recommendation_instance_id,
            "decision": payload.decision,
            "at": now,
        }
    )
    return result


@router.post(
    "/recommendations/{recommendation_instance_id}/feedback",
    status_code=201,
    response_model=FeedbackResponse,
)
def create_feedback(
    recommendation_instance_id: str,
    payload: FeedbackRequest,
    background_tasks: BackgroundTasks,
    context: Context,
    services: Registry,
    broker: Broker,
) -> FeedbackResponse:
    now = services.core.now()
    with services.core.database.write() as connection:
        result = services.recommendations.feedback(
            connection,
            tenant_id=context.tenant_id,
            recommendation_instance_id=recommendation_instance_id,
            request=payload,
            now=now,
        )
    broker.publish(
        {
            "type": "feedback.recorded",
            "recommendation_instance_id": recommendation_instance_id,
            "rating": payload.rating,
            "at": now,
        }
    )
    if payload.rating == "bad":
        background_tasks.add_task(
            _redraft_recommendation, services, broker, recommendation_instance_id
        )
    return result


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    broker: EventBroker = websocket.app.state.event_broker
    try:
        async with broker.subscribe() as queue:
            while True:
                await websocket.send_json(await queue.get())
    except WebSocketDisconnect:
        return


def _generate_recommendation(
    services: ServiceRegistry,
    broker: EventBroker,
    tenant_id: str,
    child_id: str,
    prediction_episode_id: str,
    answers: tuple[AnswerItem, ...],
) -> None:
    result = services.recommendations.generate(
        tenant_id=tenant_id,
        subject_id=child_id,
        prediction_episode_id=prediction_episode_id,
        probability=services.recommendations.probability_for_episode(prediction_episode_id),
        answers=answers,
        now=services.core.now(),
    )
    broker.publish(
        {
            "type": "recommendation.ready",
            "child_id": result.child_id,
            "prediction_episode_id": result.prediction_episode_id,
            "recommendation_instance_id": result.recommendation_instance_id,
            "status": result.status,
            "abstention_reason": result.abstention_reason,
            "at": services.core.now(),
        }
    )


def _redraft_recommendation(
    services: ServiceRegistry, broker: EventBroker, recommendation_instance_id: str
) -> None:
    result = services.recommendations.redraft(recommendation_instance_id, now=services.core.now())
    broker.publish(
        {
            "type": "recommendation.redrafted",
            "recommendation_instance_id": result.recommendation_instance_id,
            "attempt": result.attempt,
            "status": result.status,
            "at": services.core.now(),
        }
    )
