"""Las 11 rutas de producto de `SPEC 11.1`.

Una ruta valida el request, autoriza al actor, llama un servicio de aplicación y
serializa la respuesta. No contiene SQL ni fórmulas (CONVENTIONS 12.1).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from apps.api.contracts.constants import API_PREFIX
from apps.api.contracts.enums import GrantCapability
from apps.api.contracts.models import (
    AnswerAcceptedView,
    AnswerRequest,
    CreateExecutionRequest,
    CreateOutcomeReportRequest,
    CreateReviewRequest,
    EvaluationReportView,
    ExecutionView,
    FormSessionView,
    OpenFormSessionRequest,
    OutcomeReportResponse,
    OutcomeRequestListView,
    PredictionEpisodeView,
    RecommendationInboxView,
    RecommendationsView,
    ReviewView,
    SessionContextView,
    SubjectView,
    SubmitFormSessionView,
)
from apps.api.contracts.texts import EMERGENCY_NOTICE_ES
from apps.api.errors import invalid
from apps.api.routes.dependencies import Actor, IdempotencyKey, IfMatch, Registry
from apps.api.services.base import IdempotentRequest
from apps.api.store import identity

router = APIRouter(prefix=API_PREFIX)


def _command(
    request: Request,
    *,
    key: str,
    path_params: dict[str, Any],
    body: Any,
) -> IdempotentRequest:
    return IdempotentRequest(
        key=key,
        method=request.method,
        concrete_path=request.url.path,
        path_params=path_params,
        query=dict(request.query_params),
        body=body,
    )


def _json(result: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=result)


# -- contexto de sesión (soporte del frontend) ---------------------------


@router.get("/session", response_model=SessionContextView)
def session_context(actor: Actor, services: Registry) -> SessionContextView:
    """Quién soy y sobre qué sujetos tengo grant. No devuelve datos clínicos."""
    now = services.core.now()
    with services.core.database.read() as connection:
        subject_ids = services.core.authorization.granted_subject_ids(
            connection, actor=actor, capability=GrantCapability.SUBJECT_READ, cutoff=now
        )
        rows = identity.subjects_for_actor(
            connection, tenant_id=actor.tenant_id, subject_ids=subject_ids
        )
        return SessionContextView(
            actor_id=actor.actor_id,
            display_name=actor.display_name,
            tenant_id=actor.tenant_id,
            roles=sorted(actor.roles),
            subjects=[
                SubjectView(
                    subject_id=row["subject_id"],
                    display_label=row["display_label"],
                    cohort_kind=row["cohort_kind"],
                )
                for row in rows
            ],
            deployment_mode=services.core.settings.deployment_mode.value,
            adapters_source=services.core.ports.source,
            emergency_notice_es=EMERGENCY_NOTICE_ES,
        )


# -- formulario ----------------------------------------------------------


@router.post("/form-sessions", status_code=201, response_model=FormSessionView)
def open_form_session(
    request: Request,
    payload: OpenFormSessionRequest,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
) -> Response:
    body = payload.model_dump(mode="json")
    result = services.core.execute_command(
        actor=actor,
        request=_command(request, key=key, path_params={}, body=body),
        authorize_replay=lambda connection, now: services.form_sessions.authorize_open(
            connection, actor=actor, subject_id=str(payload.subject_id), now=now
        ),
        execute=lambda connection, now: (
            201,
            services.form_sessions.open(
                connection, actor=actor, request=payload, now=now
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


@router.get("/form-sessions/{form_session_id}", response_model=FormSessionView)
def read_form_session(form_session_id: str, actor: Actor, services: Registry) -> FormSessionView:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.form_sessions.view(
            connection, actor=actor, form_session_id=form_session_id, now=now
        )


@router.post(
    "/form-sessions/{form_session_id}/answers",
    status_code=201,
    response_model=AnswerAcceptedView,
)
def answer_form_session(
    request: Request,
    form_session_id: str,
    payload: AnswerRequest,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
) -> Response:
    body = payload.model_dump(mode="json")
    result = services.core.execute_command(
        actor=actor,
        request=_command(
            request, key=key, path_params={"form_session_id": form_session_id}, body=body
        ),
        authorize_replay=lambda connection, now: services.form_sessions.authorize_session(
            connection,
            actor=actor,
            form_session_id=form_session_id,
            capability=GrantCapability.DAILY_OBSERVATION_WRITE,
            now=now,
        ),
        execute=lambda connection, now: (
            201,
            services.form_sessions.answer(
                connection,
                actor=actor,
                form_session_id=form_session_id,
                request=payload,
                now=now,
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


@router.post(
    "/form-sessions/{form_session_id}/submit",
    status_code=201,
    response_model=SubmitFormSessionView,
)
def submit_form_session(
    request: Request,
    form_session_id: str,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
) -> Response:
    result = services.core.execute_command(
        actor=actor,
        request=_command(
            request, key=key, path_params={"form_session_id": form_session_id}, body=None
        ),
        authorize_replay=lambda connection, now: services.form_sessions.authorize_session(
            connection,
            actor=actor,
            form_session_id=form_session_id,
            capability=GrantCapability.FORM_SUBMIT,
            now=now,
        ),
        execute=lambda connection, now: (
            201,
            services.form_sessions.submit(
                connection, actor=actor, form_session_id=form_session_id, now=now
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


# -- predicción y outcome -------------------------------------------------


@router.get("/prediction-episodes/{prediction_episode_id}", response_model=PredictionEpisodeView)
def read_prediction_episode(
    prediction_episode_id: str, actor: Actor, services: Registry
) -> PredictionEpisodeView:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.episodes.get(
            connection, actor=actor, prediction_episode_id=prediction_episode_id, now=now
        )


@router.get("/outcome-requests", response_model=OutcomeRequestListView)
def list_outcome_requests(actor: Actor, services: Registry) -> OutcomeRequestListView:
    now = services.core.now()
    # Al pasar el deadline, `SPEC 4.4` exige materializar la resolución `unknown`
    # antes de derivar `missing`: por eso la lectura usa una transacción de
    # escritura. No crea episodios, requests ni solicitudes de autoría.
    with services.core.database.write() as connection:
        return services.outcomes.list_requests(connection, actor=actor, now=now)


@router.post(
    "/prediction-episodes/{prediction_episode_id}/outcome-reports",
    status_code=201,
    response_model=OutcomeReportResponse,
)
def create_outcome_report(
    request: Request,
    prediction_episode_id: str,
    payload: CreateOutcomeReportRequest,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
) -> Response:
    body = payload.model_dump(mode="json")
    result = services.core.execute_command(
        actor=actor,
        request=_command(
            request,
            key=key,
            path_params={"prediction_episode_id": prediction_episode_id},
            body=body,
        ),
        authorize_replay=lambda connection, now: services.outcomes.authorize_report(
            connection, actor=actor, prediction_episode_id=prediction_episode_id, now=now
        ),
        execute=lambda connection, now: (
            201,
            services.outcomes.create_report(
                connection,
                actor=actor,
                prediction_episode_id=prediction_episode_id,
                request=payload,
                now=now,
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


# -- recomendación --------------------------------------------------------


@router.get(
    "/prediction-episodes/{prediction_episode_id}/recommendations",
    response_model=RecommendationsView,
)
def read_recommendations(
    prediction_episode_id: str, actor: Actor, services: Registry, response: Response
) -> RecommendationsView:
    """SPEC 11.6 / CONVENTIONS 12.1: este GET no crea filas."""
    now = services.core.now()
    with services.core.database.read() as connection:
        view = services.recommendations.for_episode(
            connection, actor=actor, prediction_episode_id=prediction_episode_id, now=now
        )
    response.headers["ETag"] = f'"{view.revision}"'
    return view


@router.get("/recommendation-instances", response_model=RecommendationInboxView)
def read_recommendation_inbox(
    actor: Actor, services: Registry, review_status: str = "pending"
) -> RecommendationInboxView:
    if review_status != "pending":
        raise invalid("validation_error", reason="unsupported_review_status")
    now = services.core.now()
    with services.core.database.read() as connection:
        return services.recommendations.inbox(connection, actor=actor, now=now)


@router.post(
    "/recommendation-instances/{recommendation_instance_id}/reviews",
    status_code=201,
    response_model=ReviewView,
)
def create_recommendation_review(
    request: Request,
    recommendation_instance_id: str,
    payload: CreateReviewRequest,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
    revision: IfMatch,
) -> Response:
    body = payload.model_dump(mode="json")
    result = services.core.execute_command(
        actor=actor,
        request=_command(
            request,
            key=key,
            path_params={"recommendation_instance_id": recommendation_instance_id},
            body=body,
        ),
        authorize_replay=lambda connection, now: services.recommendations.authorize_instance(
            connection,
            actor=actor,
            recommendation_instance_id=recommendation_instance_id,
            capability=GrantCapability.RECOMMENDATION_REVIEW,
            now=now,
        ),
        execute=lambda connection, now: (
            201,
            services.recommendations.create_review(
                connection,
                actor=actor,
                recommendation_instance_id=recommendation_instance_id,
                request=payload,
                if_match=revision,
                now=now,
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


@router.post(
    "/recommendation-instances/{recommendation_instance_id}/executions",
    status_code=201,
    response_model=ExecutionView,
)
def create_strategy_execution(
    request: Request,
    recommendation_instance_id: str,
    payload: CreateExecutionRequest,
    actor: Actor,
    services: Registry,
    key: IdempotencyKey,
    revision: IfMatch,
) -> Response:
    body = payload.model_dump(mode="json")
    result = services.core.execute_command(
        actor=actor,
        request=_command(
            request,
            key=key,
            path_params={"recommendation_instance_id": recommendation_instance_id},
            body=body,
        ),
        authorize_replay=lambda connection, now: services.recommendations.authorize_instance(
            connection,
            actor=actor,
            recommendation_instance_id=recommendation_instance_id,
            capability=GrantCapability.EXECUTION_RECORD,
            now=now,
        ),
        execute=lambda connection, now: (
            201,
            services.recommendations.create_execution(
                connection,
                actor=actor,
                recommendation_instance_id=recommendation_instance_id,
                request=payload,
                if_match=revision,
                now=now,
            ).model_dump(mode="json"),
        ),
    )
    return _json(result.body, result.status_code)


# -- evaluación -----------------------------------------------------------


@router.get("/evaluation/{model_version}", response_model=EvaluationReportView)
def read_evaluation(model_version: str, actor: Actor, services: Registry) -> EvaluationReportView:
    now = services.core.now()
    with services.core.database.write() as connection:
        return services.evaluation.get(
            connection, actor=actor, model_version=model_version, now=now
        )
