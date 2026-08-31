"""The OpenAPI document exposes exactly the v0.4 HTTP surface."""

EXPECTED = {
    ("get", "/health"),
    ("get", "/v1/calibration"),
    ("get", "/v1/children"),
    ("get", "/v1/children/{child_id}"),
    ("get", "/v1/children/{child_id}/history"),
    ("get", "/v1/children/{child_id}/recommendations/today"),
    ("post", "/v1/children/{child_id}/form-plan"),
    ("post", "/v1/children/{child_id}/forms"),
    ("get", "/v1/prediction-episodes/{prediction_episode_id}"),
    ("post", "/v1/prediction-episodes/{prediction_episode_id}/outcome-reports"),
    ("get", "/v1/outcome-requests"),
    ("get", "/v1/prediction-episodes/{prediction_episode_id}/recommendations"),
    ("get", "/v1/recommendations"),
    ("get", "/v1/recommendations/review-queue"),
    ("post", "/v1/recommendations/{recommendation_instance_id}/feedback"),
    ("post", "/v1/recommendations/{recommendation_instance_id}/review"),
}


def test_openapi_has_only_the_v04_http_operations(app) -> None:
    schema = app.openapi()
    actual = {
        (method, path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }
    assert actual == EXPECTED


def test_no_operation_declares_removed_security_or_replay_headers(app) -> None:
    schema = app.openapi()
    for operations in schema["paths"].values():
        for operation in operations.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            names = {parameter["name"] for parameter in operation.get("parameters", [])}
            assert names.isdisjoint({"Authorization", "Idempotency-Key", "If-Match"})
            assert not operation.get("security")
