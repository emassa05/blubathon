"""FastAPI application and the only HTTP translation boundary for domain errors."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from apps.api.routes import router
from ml.errors import (
    ContractViolationError,
    FaroError,
    InsufficientDataError,
    ModelNotReadyError,
)
from ml.spec_constants import SPEC_VERSION
from packages.shared import ERROR_MESSAGES_ES

logger = logging.getLogger(__name__)
app = FastAPI(title="Faro API", version=SPEC_VERSION)
app.include_router(router)


def _error_response(code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message_es": ERROR_MESSAGES_ES[code]}},
    )


@app.exception_handler(FaroError)
async def handle_faro_error(request: Request, error: FaroError) -> JSONResponse:
    if isinstance(error, ModelNotReadyError):
        return _error_response(error.code, 503)
    if isinstance(error, (ContractViolationError, InsufficientDataError)):
        return _error_response(error.code, 422)
    return _error_response(error.code, 500)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    has_provenance_conflict = any(
        detail.get("type") == "provenance_conflict" for detail in error.errors()
    )
    code = "provenance_conflict" if has_provenance_conflict else "validation_error"
    return _error_response(code, 422)


@app.exception_handler(HTTPException)
async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
    code = (
        "not_found"
        if error.status_code == 404
        else "method_not_allowed"
        if error.status_code == 405
        else "http_error"
    )
    return _error_response(code, error.status_code)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("Unhandled API error of type %s", type(error).__name__)
    return _error_response("internal_error", 500)
