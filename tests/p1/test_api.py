from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.main import app
from apps.api.services import configure_services, get_services
from ml.errors import (
    ContractViolationError,
    FaroError,
    InsufficientDataError,
    ModelNotReadyError,
)
from ml.spec_constants import MODEL_VERSION
from packages.shared import (
    FILTER_QUESTION_ES,
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

CHILD_ID = "e7cd1d03-e4c7-4908-8c52-b612cf1d9584"
LOG_ID = "cfe4bc68-82a9-4d29-a240-b59e25b41d0a"
TARGET_DATE = date(2026, 8, 25)


class FakeServices:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.ingested_logs: list[DailyLog] = []

    def _check_error(self) -> None:
        if self.error is not None:
            raise self.error

    def ingest(self, logs: list[DailyLog]) -> IngestResponse:
        self._check_error()
        self.ingested_logs = logs
        return IngestResponse(ok=True, child_id=logs[0].child_id, date=logs[0].date)

    def predict(self, child_id: UUID, prediction_date: date) -> RiskResponse:
        self._check_error()
        return RiskResponse.model_validate(
            {
                "child_id": child_id,
                "date": prediction_date,
                "status": "insufficient_data",
                "risk": None,
                "risk_band": None,
                "interval": None,
                "confidence": None,
                "icd": 0.20,
                "requested_variables": [
                    {
                        "variable": "sleep_hours",
                        "prompt_es": "¿Cuántas horas durmió anoche?",
                        "voi": 0.12,
                    }
                ],
                "model_version": MODEL_VERSION,
                "generated_at": "2026-08-24T22:00:00Z",
            }
        )

    def voi(self, child_id: UUID, target_date: date) -> VoIResponse:
        self._check_error()
        return VoIResponse.model_validate(
            {
                "child_id": child_id,
                "date": target_date,
                "highlighted": [
                    {
                        "variable": "sleep_hours",
                        "prompt_es": "¿Cuántas horas durmió anoche?",
                        "voi": 0.12,
                        "reason": "voi",
                    },
                    {
                        "variable": "gi_status",
                        "prompt_es": "¿Tuvo molestias digestivas hoy?",
                        "voi": 0.08,
                        "reason": "voi",
                    },
                ],
                "filter_question_es": "¿Hoy pasó algo distinto o fuera de lo común?",
                "tail": [],
            }
        )

    def explain(self, child_id: UUID, target_date: date) -> ExplainResponse:
        self._check_error()
        return ExplainResponse.model_validate(
            {
                "drivers": [],
                "narrative": {
                    "headline_es": "Información en preparación",
                    "explanation_es": "Aún estamos reuniendo datos.",
                    "actions_es": [],
                },
                "narrative_source": "template",
                "strategies": [],
            }
        )

    def counterfactual(self, request: CounterfactualRequest) -> CounterfactualResponse:
        self._check_error()
        return CounterfactualResponse(
            risk_before=0.40,
            risk_after=0.20,
            band_before="rojo",
            band_after="ambar",
        )

    def quality(self, child_id: UUID, target_date: date) -> QualityResponse:
        self._check_error()
        return QualityResponse(icd=0.80, coverage=0.80, recency=1.0, consistency=1.0)

    def feedback(self, request: FeedbackRequest) -> OkResponse:
        self._check_error()
        return OkResponse(ok=True)

    def evaluation(self) -> EvaluationResponse:
        self._check_error()
        return EvaluationResponse(metrics={}, baselines={}, ablations={})


@pytest.fixture
def services() -> FakeServices:
    fake = FakeServices()
    app.dependency_overrides[get_services] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(services: FakeServices) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _daily_log() -> dict[str, object]:
    return {
        "log_id": LOG_ID,
        "child_id": CHILD_ID,
        "date": "2026-08-24",
        "source": "home",
        "sleep_hours": 8.0,
        "observed_behavior_tags": [],
        "crisis_occurred": False,
        "capture_method": "form",
        "field_provenance": {"sleep_hours": "observed"},
        "created_at": "2026-08-24T22:00:00Z",
    }


def test_all_eight_endpoints_respond(client: TestClient) -> None:
    requests = [
        client.post("/api/v1/ingest", json=_daily_log()),
        client.get("/api/v1/predict", params={"child_id": CHILD_ID, "date": TARGET_DATE}),
        client.get("/api/v1/voi", params={"child_id": CHILD_ID, "date": TARGET_DATE}),
        client.get("/api/v1/explain", params={"child_id": CHILD_ID, "date": TARGET_DATE}),
        client.post(
            "/api/v1/counterfactual",
            json={"child_id": CHILD_ID, "date": str(TARGET_DATE), "overrides": {"sleep_hours": 9}},
        ),
        client.get("/api/v1/quality", params={"child_id": CHILD_ID, "date": TARGET_DATE}),
        client.post(
            "/api/v1/feedback",
            json={"child_id": CHILD_ID, "date": str(TARGET_DATE), "dysregulation_occurred": False},
        ),
        client.get("/api/v1/eval"),
    ]
    assert all(response.status_code == 200 for response in requests)


def test_abstention_returns_http_200(client: TestClient) -> None:
    response = client.get(
        "/api/v1/predict",
        params={"child_id": CHILD_ID, "date": TARGET_DATE},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_data"


def test_ingest_accepts_lists_and_marks_explicit_empty_tags_observed(
    client: TestClient,
    services: FakeServices,
) -> None:
    first = _daily_log()
    second = _daily_log()
    second["log_id"] = "d5da1860-b119-4a35-bb11-bcdcc44a0e88"
    response = client.post("/api/v1/ingest", json=[first, second])
    assert response.status_code == 200
    assert len(services.ingested_logs) == 2
    assert services.ingested_logs[0].field_provenance["observed_behavior_tags"] == "observed"


def test_ingest_rejects_assumed_stable_with_value(client: TestClient) -> None:
    payload = _daily_log()
    payload["field_provenance"] = {"sleep_hours": "assumed_stable"}
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "provenance_conflict",
            "message_es": "La procedencia indicada no puede asignar un valor al campo.",
        }
    }


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "post",
            "/api/v1/feedback",
            {
                "child_id": CHILD_ID,
                "date": str(TARGET_DATE),
                "dysregulation_occurred": "no",
            },
        ),
        (
            "post",
            "/api/v1/ingest",
            {**_daily_log(), "created_at": "2026-08-24T22:00:00+00:00"},
        ),
    ],
)
def test_body_contract_does_not_coerce_values(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object],
) -> None:
    response = client.request(method, path, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_query_date_rejects_datetime(client: TestClient) -> None:
    response = client.get(
        "/api/v1/quality",
        params={"child_id": CHILD_ID, "date": "2026-08-25T00:00:00"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (FaroError("private detail"), 500, "faro_error"),
        (InsufficientDataError("private detail"), 422, "insufficient_data"),
        (ContractViolationError("private detail"), 422, "contract_violation"),
        (ModelNotReadyError("private detail"), 503, "model_not_ready"),
    ],
)
def test_domain_errors_are_sanitized(
    client: TestClient,
    services: FakeServices,
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    services.error = error
    response = client.get(
        "/api/v1/quality",
        params={"child_id": CHILD_ID, "date": TARGET_DATE},
    )
    assert response.status_code == status_code
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["code"] == code
    assert "private detail" not in response.text


def test_unexpected_errors_are_sanitized(
    client: TestClient,
    services: FakeServices,
) -> None:
    services.error = RuntimeError("private path and detail")
    response = client.get(
        "/api/v1/quality",
        params={"child_id": CHILD_ID, "date": TARGET_DATE},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private path" not in response.text


def test_framework_errors_use_sanitized_envelope(client: TestClient) -> None:
    not_found = client.get("/missing")
    method_not_allowed = client.delete("/api/v1/eval")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"
    assert method_not_allowed.status_code == 405
    assert method_not_allowed.json()["error"]["code"] == "method_not_allowed"


def test_openapi_documents_exactly_eight_versioned_paths(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = {path for path in response.json()["paths"] if path.startswith("/api/v1")}
    assert paths == {
        "/api/v1/ingest",
        "/api/v1/predict",
        "/api/v1/voi",
        "/api/v1/explain",
        "/api/v1/counterfactual",
        "/api/v1/quality",
        "/api/v1/feedback",
        "/api/v1/eval",
    }
    assert response.json()["paths"]["/api/v1/ingest"].keys() == {"post"}
    assert response.json()["paths"]["/api/v1/predict"].keys() == {"get"}
    assert all(
        "500" in operation["responses"]
        for path in paths
        for operation in response.json()["paths"][path].values()
    )


def test_docs_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


def test_service_registry_accepts_p2_composition(services: FakeServices) -> None:
    previous = get_services()
    configure_services(services)
    assert get_services() is services
    configure_services(previous)


def test_response_models_reject_inconsistent_success_states() -> None:
    with pytest.raises(ValidationError, match="risk_band"):
        RiskResponse.model_validate(
            {
                "child_id": CHILD_ID,
                "date": str(TARGET_DATE),
                "status": "ok",
                "risk": 0.40,
                "risk_band": "verde",
                "interval": [0.30, 0.50],
                "confidence": "alta",
                "icd": 0.80,
                "requested_variables": [],
                "model_version": MODEL_VERSION,
                "generated_at": "2026-08-24T22:00:00Z",
            }
        )
    with pytest.raises(ValidationError, match="counterfactual band"):
        CounterfactualResponse(
            risk_before=0.40,
            risk_after=0.20,
            band_before="verde",
            band_after="ambar",
        )
    highlighted_item = {
        "variable": "sleep_hours",
        "prompt_es": "¿Cuántas horas durmió anoche?",
        "voi": 0.12,
        "reason": "voi",
    }
    # SPEC 7.5a: the block never grows past three, even when more variables
    # reach the staleness ceiling on the same day.
    with pytest.raises(ValidationError, match="at most 3"):
        VoIResponse.model_validate(
            {
                "child_id": CHILD_ID,
                "date": str(TARGET_DATE),
                "highlighted": [highlighted_item] * 4,
                "filter_question_es": FILTER_QUESTION_ES,
                "tail": [],
            }
        )
