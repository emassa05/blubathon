"""OpenAPI contra el contrato (SPEC 11.1, 20.18; gate de `TAREAS 11`).

Verifica que el documento publicado tenga exactamente las 11 rutas de producto,
que use los modelos compartidos (no `dict` libres) y que se deshabilite en modo
piloto (CONVENTIONS 15).
"""

from __future__ import annotations

from apps.api.contracts.constants import API_PREFIX

# SPEC 11.1, tabla de rutas de producto.
PRODUCT_ROUTES: set[tuple[str, str]] = {
    ("post", f"{API_PREFIX}/form-sessions"),
    ("post", f"{API_PREFIX}/form-sessions/{{form_session_id}}/answers"),
    ("post", f"{API_PREFIX}/form-sessions/{{form_session_id}}/submit"),
    ("get", f"{API_PREFIX}/prediction-episodes/{{prediction_episode_id}}"),
    ("get", f"{API_PREFIX}/outcome-requests"),
    ("post", f"{API_PREFIX}/prediction-episodes/{{prediction_episode_id}}/outcome-reports"),
    ("get", f"{API_PREFIX}/prediction-episodes/{{prediction_episode_id}}/recommendations"),
    ("get", f"{API_PREFIX}/recommendation-instances"),
    ("post", f"{API_PREFIX}/recommendation-instances/{{recommendation_instance_id}}/reviews"),
    (
        "post",
        f"{API_PREFIX}/recommendation-instances/{{recommendation_instance_id}}/executions",
    ),
    ("get", f"{API_PREFIX}/evaluation/{{model_version}}"),
}

# Rutas de soporte que no pertenecen a la tabla del SPEC pero sí al despliegue.
SUPPORT_ROUTES: set[tuple[str, str]] = {
    ("get", "/health"),
    ("get", f"{API_PREFIX}/session"),
    ("get", f"{API_PREFIX}/form-sessions/{{form_session_id}}"),
}


def _operations(document: dict) -> set[tuple[str, str]]:
    return {
        (method, path)
        for path, item in document["paths"].items()
        for method in item
        if method in ("get", "post", "put", "patch", "delete")
    }


def test_openapi_publishes_exactly_the_eleven_product_routes(client) -> None:
    document = client.get("/openapi.json").json()
    operations = _operations(document)
    assert operations >= PRODUCT_ROUTES
    assert operations - PRODUCT_ROUTES == SUPPORT_ROUTES


def test_every_response_has_an_explicit_model(client) -> None:
    """CONVENTIONS 6: ningún `dict[str, object]` sustituye un contrato."""
    document = client.get("/openapi.json").json()
    for method, path in PRODUCT_ROUTES:
        operation = document["paths"][path][method]
        success = next((code for code in operation["responses"] if code.startswith("2")), None)
        assert success is not None, f"{method} {path} no declara respuesta exitosa"
        schema = operation["responses"][success]["content"]["application/json"]["schema"]
        assert "$ref" in schema, f"{method} {path} no usa un modelo explícito"


def test_every_post_declares_the_idempotency_key_header(client) -> None:
    document = client.get("/openapi.json").json()
    for method, path in PRODUCT_ROUTES:
        if method != "post":
            continue
        names = {
            parameter["name"] for parameter in document["paths"][path][method].get("parameters", [])
        }
        assert "Idempotency-Key" in names, f"{path} no declara Idempotency-Key"


def test_review_and_execution_declare_if_match(client) -> None:
    document = client.get("/openapi.json").json()
    for path in (
        f"{API_PREFIX}/recommendation-instances/{{recommendation_instance_id}}/reviews",
        f"{API_PREFIX}/recommendation-instances/{{recommendation_instance_id}}/executions",
    ):
        names = {
            parameter["name"] for parameter in document["paths"][path]["post"].get("parameters", [])
        }
        assert "If-Match" in names


def test_request_models_forbid_unknown_fields(client) -> None:
    """`extra="forbid"` en fronteras de API (CONVENTIONS 6)."""
    document = client.get("/openapi.json").json()
    for name in ("FormSessionCreateRequest", "AnswerRequest", "OutcomeReportRequest"):
        schema = document["components"]["schemas"][name]
        assert schema.get("additionalProperties") is False, name


def test_openapi_is_disabled_in_pilot_mode(tmp_path) -> None:
    from apps.api.main import create_app
    from apps.api.settings import Settings

    application = create_app(
        settings=Settings(
            mode="pilot",  # type: ignore[arg-type]
            database_url="postgresql://localhost/faro",
            db_path=tmp_path / "pilot.db",
        ),
        migrate=True,
    )
    assert application.openapi_url is None
    assert application.docs_url is None
