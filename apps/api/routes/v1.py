"""The eight frozen HTTP endpoints from SPEC section 11."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import UUID4

from apps.api.services import ApiServices, get_services
from ml.spec_constants import API_PREFIX
from packages.shared import (
    CanonicalDate,
    CounterfactualRequest,
    CounterfactualResponse,
    DailyLog,
    ErrorResponse,
    EvaluationResponse,
    ExplainResponse,
    FeedbackRequest,
    IngestResponse,
    OkResponse,
    QualityResponse,
    RiskResponse,
    VoIResponse,
)

router = APIRouter(prefix=API_PREFIX)
ServiceDependency = Annotated[ApiServices, Depends(get_services)]
ERROR_RESPONSES = {
    422: {"model": ErrorResponse, "description": "Contract or request validation error"},
    500: {"model": ErrorResponse, "description": "Sanitized internal error"},
    503: {"model": ErrorResponse, "description": "Model or service not ready"},
}


@router.post("/ingest", response_model=IngestResponse, responses=ERROR_RESPONSES)
def ingest(payload: DailyLog | list[DailyLog], services: ServiceDependency) -> IngestResponse:
    logs = payload if isinstance(payload, list) else [payload]
    return services.ingest(logs)


@router.get("/predict", response_model=RiskResponse, responses=ERROR_RESPONSES)
def predict(
    child_id: Annotated[UUID4, Query()],
    target_date: Annotated[CanonicalDate, Query(alias="date")],
    services: ServiceDependency,
) -> RiskResponse:
    return services.predict(child_id, target_date)


@router.get("/voi", response_model=VoIResponse, responses=ERROR_RESPONSES)
def voi(
    child_id: Annotated[UUID4, Query()],
    target_date: Annotated[CanonicalDate, Query(alias="date")],
    services: ServiceDependency,
) -> VoIResponse:
    return services.voi(child_id, target_date)


@router.get("/explain", response_model=ExplainResponse, responses=ERROR_RESPONSES)
def explain(
    child_id: Annotated[UUID4, Query()],
    target_date: Annotated[CanonicalDate, Query(alias="date")],
    services: ServiceDependency,
) -> ExplainResponse:
    return services.explain(child_id, target_date)


@router.post(
    "/counterfactual",
    response_model=CounterfactualResponse,
    responses=ERROR_RESPONSES,
)
def counterfactual(
    payload: CounterfactualRequest,
    services: ServiceDependency,
) -> CounterfactualResponse:
    return services.counterfactual(payload)


@router.get("/quality", response_model=QualityResponse, responses=ERROR_RESPONSES)
def quality(
    child_id: Annotated[UUID4, Query()],
    target_date: Annotated[CanonicalDate, Query(alias="date")],
    services: ServiceDependency,
) -> QualityResponse:
    return services.quality(child_id, target_date)


@router.post("/feedback", response_model=OkResponse, responses=ERROR_RESPONSES)
def feedback(payload: FeedbackRequest, services: ServiceDependency) -> OkResponse:
    return services.feedback(payload)


@router.get("/eval", response_model=EvaluationResponse, responses=ERROR_RESPONSES)
def evaluation(services: ServiceDependency) -> EvaluationResponse:
    return services.evaluation()
