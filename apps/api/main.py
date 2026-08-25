"""Aplicación FastAPI de Faro v0.3.

Única frontera de traducción HTTP. La abstención es HTTP 200 con estado
explícito y nunca usa el sobre de error (SPEC 11.7, CONVENTIONS 12.2).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from apps.api.adapters import build_ports
from apps.api.clock import Clock, system_clock
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.errors import ERROR_MESSAGES_ES, FaroApiError
from apps.api.routes import router
from apps.api.services import Services, build_registry
from apps.api.settings import Settings, load_settings
from apps.api.store import audit
from apps.api.store.db import Database

logger = logging.getLogger("faro.api")


def create_app(
    *,
    settings: Settings | None = None,
    clock: Clock = system_clock,
    migrate: bool = True,
) -> FastAPI:
    resolved = settings or load_settings()
    resolved.validate()
    database = Database(resolved, clock=clock)
    if migrate:
        database.migrate()
    core = Services(
        settings=resolved,
        database=database,
        ports=build_ports(secret=resolved.audit_secret),
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        database.close()

    app = FastAPI(
        title="Faro API",
        version=SPEC_VERSION,
        lifespan=lifespan,
        # CONVENTIONS 15: la documentación OpenAPI se deshabilita en piloto.
        docs_url="/docs" if resolved.expose_openapi else None,
        redoc_url=None,
        openapi_url="/openapi.json" if resolved.expose_openapi else None,
    )
    app.state.settings = resolved
    app.state.registry = build_registry(core)
    app.add_middleware(
        CORSMiddleware,
        # CONVENTIONS 15: allowlist explícita, nunca comodín.
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "If-Match"],
        expose_headers=["ETag"],
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


def _flush_audit(request: Request, error: FaroApiError) -> None:
    """SPEC 13.2: una denegación queda auditada aunque el comando se revierta."""
    intent = error.audit
    if intent is None:  # pragma: no cover - defensivo
        return
    registry = request.app.state.registry
    with registry.core.database.write() as connection:
        audit.record(
            connection,
            actor=None,
            action=intent.action,
            resource_type=intent.resource_type,
            resource_id=intent.resource_id,
            subject_id=intent.subject_id,
            tenant_id=intent.tenant_id,
            actor_id=intent.actor_id,
            decision=intent.decision,
            reason_code=intent.reason_code,
            occurred_at=registry.core.now(),
            request_id=intent.request_id or getattr(request.state, "request_id", "unknown"),
        )


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(FaroApiError)
    async def handle_domain_error(request: Request, error: FaroApiError) -> JSONResponse:
        if error.audit is not None:
            _flush_audit(request, error)
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
