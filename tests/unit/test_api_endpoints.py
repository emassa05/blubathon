"""Los 8 endpoints (§11), de punta a punta contra la DB sembrada de fixtures."""

CHILD_CALM = "00000000-0000-0000-0000-000000000001"
CHILD_HIGH = "00000000-0000-0000-0000-000000000002"
CHILD_ABSTAIN = "00000000-0000-0000-0000-000000000003"


def test_predict_ok_para_nino_calmo(client):
    r = client.get("/api/v1/predict", params={"child_id": CHILD_CALM, "date": "2026-08-14"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["risk_band"] == "verde"
    assert body["confidence"] is not None
    assert body["icd"] is not None


def test_voi_devuelve_highlighted_filter_y_tail(client):
    r = client.get("/api/v1/voi", params={"child_id": CHILD_HIGH, "date": "2026-08-05"})
    assert r.status_code == 200
    body = r.json()
    assert "highlighted" in body
    assert "filter_question_es" in body
    assert "tail" in body


def test_explain_devuelve_narrativa_valida_con_ollama_apagado(client):
    r = client.get("/api/v1/explain", params={"child_id": CHILD_HIGH, "date": "2026-08-09"})
    assert r.status_code == 200
    body = r.json()
    assert body["narrative_source"] in ("llm", "template")
    assert body["narrative"]["headline_es"]
    assert isinstance(body["strategies"], list)


def test_counterfactual(client):
    r = client.post(
        "/api/v1/counterfactual",
        json={
            "child_id": CHILD_HIGH,
            "date": "2026-08-09",
            "overrides": {"sleep_hours": 9.0, "routine_changes": False},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["risk_after"] < body["risk_before"]


def test_quality(client):
    r = client.get("/api/v1/quality", params={"child_id": CHILD_CALM, "date": "2026-08-14"})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["icd"] <= 1.0


def test_feedback(client):
    r = client.post(
        "/api/v1/feedback",
        json={
            "child_id": CHILD_HIGH,
            "date": "2026-08-09",
            "dysregulation_occurred": True,
            "strategy_used": "advance_sleep",
            "helped": True,
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_ingest_lista_de_logs(client):
    r = client.post(
        "/api/v1/ingest",
        json=[
            {
                "child_id": CHILD_CALM,
                "date": "2026-08-21",
                "source": "home",
                "sleep_hours": 8.0,
                "field_provenance": {"sleep_hours": "observed"},
            },
            {
                "child_id": CHILD_CALM,
                "date": "2026-08-22",
                "source": "home",
                "sleep_hours": 7.5,
                "field_provenance": {"sleep_hours": "observed"},
            },
        ],
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ingest_rechaza_provenance_conflict(client):
    r = client.post(
        "/api/v1/ingest",
        json={
            "child_id": CHILD_CALM,
            "date": "2026-08-21",
            "source": "home",
            "gi_status": 4,
            "field_provenance": {"gi_status": "assumed_stable"},
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "provenance_conflict"


def test_eval(client):
    r = client.get("/api/v1/eval")
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert "baselines" in body


def test_openapi_describe_los_8_endpoints(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = {
        "/api/v1/ingest",
        "/api/v1/predict",
        "/api/v1/voi",
        "/api/v1/explain",
        "/api/v1/counterfactual",
        "/api/v1/quality",
        "/api/v1/feedback",
        "/api/v1/eval",
    }
    assert expected.issubset(set(paths))
