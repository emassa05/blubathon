"""Blubathon v0.4 FastAPI application.

Única frontera de traducción HTTP. La abstención es HTTP 200 con estado
explícito y nunca usa el sobre de error (SPEC 11.7, CONVENTIONS 12.2).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from apps.api.adapters import build_ports
from apps.api.clock import Clock, system_clock
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.errors import ERROR_MESSAGES_ES, BlubathonApiError
from apps.api.events import EventBroker
from apps.api.routes import router
from apps.api.services import Services, build_registry
from apps.api.settings import Settings, load_settings
from apps.api.store.db import Database

logging.basicConfig(
    level=os.environ.get("BLUBATHON_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("blubathon.api")


def _draft_transport_from_env() -> Any | None:
    """`BLUBATHON_DRAFT_LLM` habilita la redacción real del RAG.

    Sin esto no hay LLM y toda recomendación abstiene con `draft_unavailable`,
    que es la respuesta honesta y no una falla.
    """

    chosen = os.environ.get("BLUBATHON_DRAFT_LLM")
    if chosen is None:
        return None
    if chosen == "anthropic":
        from rag.authoring.transports import AnthropicDraftTransport

        return AnthropicDraftTransport()
    if chosen == "ollama":
        from rag.authoring.transports import OLLAMA_MODEL, OLLAMA_URL, OllamaDraftTransport

        return OllamaDraftTransport(
            model=os.environ.get("BLUBATHON_OLLAMA_MODEL", OLLAMA_MODEL),
            base_url=os.environ.get("BLUBATHON_OLLAMA_URL", OLLAMA_URL),
        )
    raise ValueError(f"BLUBATHON_DRAFT_LLM desconocido: {chosen}")


def create_app(
    *,
    settings: Settings | None = None,
    clock: Clock = system_clock,
    migrate: bool = True,
    draft_transport: Any | None = None,
) -> FastAPI:
    resolved = settings or load_settings()
    resolved.validate()
    database = Database(resolved, clock=clock)
    if migrate:
        database.migrate()
    core = Services(
        settings=resolved,
        database=database,
        ports=build_ports(secret=resolved.audit_secret, database=database),
        clock=clock,
        draft_transport=draft_transport or _draft_transport_from_env(),
    )
    event_broker = EventBroker()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        event_broker.bind(asyncio.get_running_loop())
        yield
        database.close()

    app = FastAPI(
        title="Blubathon API",
        version=SPEC_VERSION,
        lifespan=lifespan,
        # CONVENTIONS 15: la documentación OpenAPI se deshabilita en piloto.
        docs_url="/docs" if resolved.expose_openapi else None,
        redoc_url=None,
        openapi_url="/openapi.json" if resolved.expose_openapi else None,
    )
    app.state.settings = resolved
    app.state.registry = build_registry(core)
    app.state.event_broker = event_broker
    app.add_middleware(
        CORSMiddleware,
        # CONVENTIONS 15: allowlist explícita, nunca comodín.
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    _install_handlers(app)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "spec_version": SPEC_VERSION,
            "mode": resolved.deployment_mode.value,
            "adapters": core.ports.source,
        }

    return app


def _envelope(request: Request, code: str, status_code: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message_es": ERROR_MESSAGES_ES.get(code, ERROR_MESSAGES_ES["internal_error"]),
                "request_id": request_id,
            }
        },
        headers={"X-Request-Id": request_id},
    )


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(BlubathonApiError)
    async def handle_domain_error(request: Request, error: BlubathonApiError) -> JSONResponse:
        return _envelope(request, error.code, error.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        # CONVENTIONS 12.2: validación es 422 y no filtra el payload clínico.
        return _envelope(request, "validation_error", 422)

    @app.exception_handler(HTTPException)
    async def handle_http(request: Request, error: HTTPException) -> JSONResponse:
        code = {
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }.get(error.status_code, "internal_error")
        return _envelope(request, code, error.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
        # Stack y request ID sí; payload clínico nunca (CONVENTIONS 15).
        logger.exception(
            "error inesperado type=%s request_id=%s",
            type(error).__name__,
            getattr(request.state, "request_id", "unknown"),
        )
        return _envelope(request, "internal_error", 500)


def _default_app() -> FastAPI:
    """Instancia por defecto para `uvicorn apps.api.main:app`."""
    return create_app()
