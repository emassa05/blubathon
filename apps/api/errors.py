"""Traducción de excepciones de `ml/` a HTTP — CONVENTIONS §6. Solo aquí."""

from __future__ import annotations

from ml.errors import ContractViolationError, FaroError, InsufficientDataError, ModelNotReadyError

_CODE_BY_EXCEPTION = {
    InsufficientDataError: ("insufficient_data", 422),
    ContractViolationError: ("provenance_conflict", 400),
    ModelNotReadyError: ("model_not_ready", 503),
}


def error_body(exc: FaroError) -> tuple[dict, int]:
    code, status = _CODE_BY_EXCEPTION.get(type(exc), ("internal_error", 500))
    return {"error": {"code": code, "message_es": str(exc)}}, status
