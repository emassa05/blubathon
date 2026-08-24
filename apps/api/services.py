"""Service boundary between P1-owned HTTP routes and P2-owned implementations."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from ml.errors import ModelNotReadyError
from packages.shared import (
    CounterfactualRequest,
    CounterfactualResponse,
    DailyLog,
    EvaluationResponse,
    ExplainResponse,
    FeedbackRequest,
    IngestResponse,
    OkResponse,
    QualityResponse,
    RiskResponse,
    VoIResponse,
)


class ApiServices(Protocol):
    """Operations supplied by the store, VoI, narrative, and evaluation domains."""

    def ingest(self, logs: list[DailyLog]) -> IngestResponse: ...

    def predict(self, child_id: UUID, prediction_date: date) -> RiskResponse: ...

    def voi(self, child_id: UUID, target_date: date) -> VoIResponse: ...

    def explain(self, child_id: UUID, target_date: date) -> ExplainResponse: ...

    def counterfactual(self, request: CounterfactualRequest) -> CounterfactualResponse: ...

    def quality(self, child_id: UUID, target_date: date) -> QualityResponse: ...

    def feedback(self, request: FeedbackRequest) -> OkResponse: ...

    def evaluation(self) -> EvaluationResponse: ...


class _UnavailableServices:
    def _raise(self) -> None:
        raise ModelNotReadyError("API services have not been configured")

    def ingest(self, logs: list[DailyLog]) -> IngestResponse:
        self._raise()

    def predict(self, child_id: UUID, prediction_date: date) -> RiskResponse:
        self._raise()

    def voi(self, child_id: UUID, target_date: date) -> VoIResponse:
        self._raise()

    def explain(self, child_id: UUID, target_date: date) -> ExplainResponse:
        self._raise()

    def counterfactual(self, request: CounterfactualRequest) -> CounterfactualResponse:
        self._raise()

    def quality(self, child_id: UUID, target_date: date) -> QualityResponse:
        self._raise()

    def feedback(self, request: FeedbackRequest) -> OkResponse:
        self._raise()

    def evaluation(self) -> EvaluationResponse:
        self._raise()


_services: ApiServices = _UnavailableServices()


def configure_services(services: ApiServices) -> None:
    """Register the concrete P2 service composition at application startup."""
    global _services
    _services = services


def get_services() -> ApiServices:
    return _services
