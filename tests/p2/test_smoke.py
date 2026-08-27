"""Fixed-tenant child and health surface."""

from __future__ import annotations

from tools.seed import ids


def test_health_reports_v04_without_authentication(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["spec_version"] == "0.4.0"


def test_children_are_filtered_to_the_fixed_tenant(client) -> None:
    response = client.get("/v1/children")
    assert response.status_code == 200
    child_ids = {item["child_id"] for item in response.json()["children"]}
    assert str(ids.SUBJECT_ANA) in child_ids
    assert str(ids.SUBJECT_SIN_GRANT) in child_ids
    assert str(ids.SUBJECT_TENANT_B) not in child_ids


def test_child_exposes_active_profile_and_open_episode(client) -> None:
    response = client.get(f"/v1/children/{ids.SUBJECT_ANA}")
    assert response.status_code == 200
    body = response.json()
    assert body["child_id"] == str(ids.SUBJECT_ANA)
    assert body["care_mode"] == "home_and_therapy"
    assert body["prediction_episode_id"] is None


def test_no_product_endpoint_requires_auth_headers(client) -> None:
    for path in ("/v1/children", f"/v1/children/{ids.SUBJECT_ANA}", "/v1/outcome-requests"):
        assert client.get(path).status_code not in {401, 403}
