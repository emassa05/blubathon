"""Arranque, salud y contexto de sesión."""

from __future__ import annotations

from tools.seed import ids


def test_health_reports_spec_version_and_adapter_source(client) -> None:
    body = client.get("/health").json()
    assert body["spec_version"] == "0.3.0"
    assert body["mode"] == "demo"
    assert body["adapters"] == "mock"


def test_session_context_lists_only_granted_subjects(caregiver) -> None:
    body = caregiver.get("/api/v1/session").json()
    assert body["roles"] == ["caregiver"]
    labels = {item["subject_id"] for item in body["subjects"]}
    assert labels == {ids.SUBJECT_ANA, ids.SUBJECT_BETO}
    assert ids.SUBJECT_SIN_GRANT not in labels


def test_unauthenticated_request_is_401(client) -> None:
    response = client.get("/api/v1/session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.json()["error"]["request_id"]
