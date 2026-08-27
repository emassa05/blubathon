"""Errores de dominio y su traducción HTTP (SPEC 11.7, CONVENTIONS 12.2).

Un error lleva código estable, mensaje en español sanitizado y `request_id`.
La abstención **no** usa este sobre: es HTTP 200 con estado explícito.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Cada código es estable y no revela payload clínico.
ERROR_MESSAGES_ES: dict[str, str] = {
    "authentication_required": "Necesitas iniciar sesión para continuar.",
    "forbidden": "No tienes autorización para esta operación.",
    "validation_error": "Los datos enviados no cumplen el contrato.",
    "field_not_allowed_for_source": "Ese campo no se registra desde esta fuente.",
    "default_presentation_not_current": "La sugerencia mostrada ya no está vigente.",
    "not_found": "No encontramos el recurso solicitado.",
    "method_not_allowed": "Operación no permitida en esta ruta.",
    "revision_conflict": "El recurso cambió desde tu última lectura.",
    "outcome_report_invalid_timing": "El momento declarado no cae en la ventana del objetivo.",
    "outcome_occurred_at_required": "Un reporte afirmativo necesita cuándo ocurrió.",
    "outcome_occurred_at_forbidden": "Solo un reporte afirmativo declara cuándo ocurrió.",
    "pilot_requires_postgresql": "El modo piloto no arranca sobre SQLite.",
    "internal_error": "Ocurrió un error inesperado. El equipo quedó notificado.",
}


@dataclass(slots=True)
class FaroApiError(Exception):
    """Error de dominio con traducción HTTP determinista."""

    code: str
    status_code: int = 400
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.code)

    @property
    def message_es(self) -> str:
        return ERROR_MESSAGES_ES.get(self.code, ERROR_MESSAGES_ES["internal_error"])


def invalid(code: str = "validation_error", **detail: Any) -> FaroApiError:
    return FaroApiError(code, 422, detail)


def conflict(code: str, **detail: Any) -> FaroApiError:
    return FaroApiError(code, 409, detail)


def not_found(code: str = "not_found", **detail: Any) -> FaroApiError:
    return FaroApiError(code, 404, detail)
