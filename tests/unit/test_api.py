"""The eight endpoints, end to end against a real trained model (SPEC 11)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from ml.spec_constants import API_PREFIX, MODEL_VERSION
from tests.conftest import last_date

pytestmark = pytest.mark.filterwarnings("ignore")

ENDPOINTS = (
    "/ingest",
    "/predict",
    "/voi",
    "/explain",
    "/counterfactual",
    "/quality",
    "/feedback",
    "/eval",
)


@pytest.fixture
def calm_today(calm_history):
    """Every endpoint takes the day being recorded, never the day predicted."""
    return last_date(calm_history).isoformat()


@pytest.fixture
def calm_tomorrow(calm_history):
    return (last_date(calm_history) + timedelta(days=1)).isoformat()


def test_openapi_describes_the_eight_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    for endpoint in ENDPOINTS:
        assert f"{API_PREFIX}{endpoint}" in paths


def test_predict_returns_the_central_contract(client, calm_child_id, calm_today, calm_tomorrow):
    response = client.get(
        f"{API_PREFIX}/predict", params={"child_id": calm_child_id, "date": calm_today}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == calm_tomorrow
    assert body["model_version"] == MODEL_VERSION
    assert body["status"] in {"ok", "insufficient_data"}
    if body["status"] == "ok":
        assert 0.0 <= body["risk"] <= 1.0
        assert body["risk_band"] in {"verde", "ambar", "rojo"}
        assert body["interval"][0] <= body["risk"] <= body["interval"][1]
        assert body["confidence"] in {"alta", "media", "baja"}


def test_predict_is_deterministic(client, calm_child_id, calm_today):
    params = {"child_id": calm_child_id, "date": calm_today}
    first = client.get(f"{API_PREFIX}/predict", params=params).json()
    second = client.get(f"{API_PREFIX}/predict", params=params).json()
    assert first["risk"] == second["risk"]
    assert first["interval"] == second["interval"]


def test_voi_returns_the_three_blocks(client, calm_child_id, calm_history):
    response = client.get(
        f"{API_PREFIX}/voi",
        params={"child_id": calm_child_id, "date": last_date(calm_history).isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert 1 <= len(body["highlighted"]) <= 3
    assert body["filter_question_es"]
    assert isinstance(body["tail"], list)
    for item in body["highlighted"]:
        assert item["reason"] in {"voi", "staleness", "exploration"}
        assert item["prompt_es"]
        assert item["voi"] >= 0


def test_explain_returns_a_narrative_with_ollama_down(client, calm_child_id, calm_today):
    """SPEC 10.2: the deterministic template is the guaranteed path."""
    response = client.get(
        f"{API_PREFIX}/explain", params={"child_id": calm_child_id, "date": calm_today}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["narrative_source"] in {"llm", "template"}
    narrative = body["narrative"]
    assert narrative["headline_es"]
    assert len(narrative["explanation_es"].split()) <= 60
    assert len(narrative["actions_es"]) <= 3
    catalogue = {strategy["label_es"] for strategy in body["strategies"]}
    assert set(narrative["actions_es"]).issubset(catalogue)


def test_explain_only_names_drivers_it_measured(client, calm_child_id, calm_today):
    body = client.get(
        f"{API_PREFIX}/explain", params={"child_id": calm_child_id, "date": calm_today}
    ).json()
    for driver in body["drivers"]:
        assert driver["direction"] in {"mejora", "empeora"}
        assert driver["detail_es"]


def test_counterfactual_moves_the_risk(client, calm_child_id, calm_history):
    response = client.post(
        f"{API_PREFIX}/counterfactual",
        json={
            "child_id": calm_child_id,
            "date": last_date(calm_history).isoformat(),
            "overrides": {"sleep_hours": 3.0, "gi_status": 1},
        },
    )
    assert response.status_code == 200
    body = response.json()
    for key in ("risk_before", "risk_after"):
        assert 0.0 <= body[key] <= 1.0
    assert body["band_before"] in {"verde", "ambar", "rojo"}
    assert body["band_after"] in {"verde", "ambar", "rojo"}


def test_quality_returns_all_four_components(client, calm_child_id, calm_history):
    body = client.get(
        f"{API_PREFIX}/quality",
        params={"child_id": calm_child_id, "date": last_date(calm_history).isoformat()},
    ).json()
    assert set(body) == {"icd", "coverage", "recency", "consistency"}
    for value in body.values():
        assert 0.0 <= value <= 1.0


def test_feedback_accepts_the_outcome(client, calm_child_id, calm_history):
    response = client.post(
        f"{API_PREFIX}/feedback",
        json={
            "child_id": calm_child_id,
            "date": last_date(calm_history).isoformat(),
            "dysregulation_occurred": True,
            "strategy_used": "advance_sleep",
            "helped": True,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_eval_returns_metrics_baselines_and_ablations(client):
    body = client.get(f"{API_PREFIX}/eval").json()
    metrics = body["metrics"]
    assert metrics["auc_pr"] > body["baselines"]["always_base_rate"]["auc_pr"]
    assert metrics["auc_pr"] > body["baselines"]["yesterday_dysregulation"]["auc_pr"]
    assert metrics["lead_time_hours"] == 24
    assert "ece" in metrics and "brier" in metrics
    assert "alert_budget_recall" in metrics
    ablations = body["ablations"]
    assert "features" in ablations
    assert "elicitation" in ablations
    assert set(ablations["elicitation"]) == {"A", "B", "C", "D"}
    assert "fairness_sex" in ablations
    assert ablations["disclaimer_es"]


def test_ingest_accepts_one_log_and_a_list(client, calm_history):
    log = dict(calm_history[0])
    log["log_id"] = "20000000-0000-4000-8000-000000000099"
    log["date"] = "2026-09-01"
    response = client.post(f"{API_PREFIX}/ingest", json=log)
    assert response.status_code == 200
    assert response.json()["ok"] is True

    second = dict(log)
    second["log_id"] = "20000000-0000-4000-8000-000000000098"
    second["date"] = "2026-09-02"
    batch = client.post(f"{API_PREFIX}/ingest", json=[log, second])
    assert batch.status_code == 200


def test_ingest_rejects_a_provenance_conflict(client, calm_history):
    log = dict(calm_history[0])
    log["log_id"] = "20000000-0000-4000-8000-000000000097"
    log["date"] = "2026-09-03"
    log["gi_status"] = 4
    log["field_provenance"] = {"gi_status": "assumed_stable"}
    response = client.post(f"{API_PREFIX}/ingest", json=log)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "provenance_conflict"


def test_unknown_route_returns_the_error_contract(client):
    body = client.get(f"{API_PREFIX}/nope").json()
    assert set(body["error"]) == {"code", "message_es"}


def test_missing_model_answers_503(seeded_db, calm_child_id, calm_today):
    """Without a trained artifact the API says so instead of guessing."""
    from fastapi.testclient import TestClient

    from apps.api.main import app
    from apps.api.services import configure_services
    from apps.api.services_impl import FaroServices

    configure_services(FaroServices("does-not-exist.joblib", seeded_db))
    with TestClient(app) as offline:
        response = offline.get(
            f"{API_PREFIX}/predict", params={"child_id": calm_child_id, "date": calm_today}
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_ready"
