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
    "invalid_credentials": "La sesión local no es válida.",
    "forbidden": "No tienes autorización para esta operación.",
    "cross_tenant": "No tienes autorización para esta organización.",
    "subject_access_denied": "No tienes una autorización vigente sobre esta persona.",
    "accreditation_required": "Necesitas una acreditación vigente para esta operación.",
    "capability_required": "Tu autorización no incluye esta capacidad.",
    "role_not_allowed": "Tu rol no permite esta operación.",
    "validation_error": "Los datos enviados no cumplen el contrato.",
    "unmapped_source_value": "La importación trae una categoría que no está mapeada.",
    "field_not_allowed_for_source": "Ese campo no se registra desde esta fuente.",
    "default_presentation_not_current": "La sugerencia mostrada ya no está vigente.",
    "form_session_not_open": "Esta sesión de formulario ya está cerrada.",
    "not_found": "No encontramos el recurso solicitado.",
    "method_not_allowed": "Operación no permitida en esta ruta.",
    "idempotency_key_required": "Falta la cabecera Idempotency-Key.",
    "idempotency_key_conflict": "Esa clave de idempotencia ya se usó con otro contenido.",
    "precondition_required": "Falta la cabecera If-Match para un recurso con revisión.",
    "revision_conflict": "El recurso cambió desde tu última lectura.",
    "outcome_report_invalid_timing": "El momento declarado no cae en la ventana del objetivo.",
    "outcome_occurred_at_required": "Un reporte afirmativo necesita cuándo ocurrió.",
    "outcome_occurred_at_forbidden": "Solo un reporte afirmativo declara cuándo ocurrió.",
    "outcome_request_closed": "La ventana de captura de este objetivo ya cerró.",
    "target_definition_ambiguous": "Hay más de una definición de objetivo vigente.",
    "recommendation_dependency_suspended": "Una dependencia de esta recomendación está suspendida.",
    "review_role_not_permitted": "Tu rol no puede aprobar ni sustituir esta estrategia.",
    "execution_role_not_permitted": "Tu rol no puede registrar esta aplicación.",
    "execution_target_ambiguous": "Una aplicación referencia una estrategia o un plan, no ambos.",
    "human_plan_roles_not_subset": "El plan humano no puede ampliar los roles de ejecución.",
    "cohort_not_allowed": "Este modo de despliegue solo acepta la cohorte de demostración.",
    "pilot_requires_postgresql": "El modo piloto no arranca sobre SQLite.",
    "internal_error": "Ocurrió un error inesperado. El equipo quedó notificado.",
}


@dataclass(frozen=True, slots=True)
class AuditIntent:
    """Evento de auditoría que debe sobrevivir al rollback del comando.

    `SPEC 13.2` exige que una denegación quede auditada. Como la transacción del
    comando se revierte al fallar, el evento viaja con el error y lo escribe el
    handler HTTP en su propia transacción.
    """

    action: str
    resource_type: str
    decision: str
    reason_code: str
    tenant_id: str | None = None
    actor_id: str | None = None
    resource_id: str | None = None
    subject_id: str | None = None
    request_id: str = ""


@dataclass(slots=True)
class FaroApiError(Exception):
    """Error de dominio con traducción HTTP determinista."""

    code: str
    status_code: int = 400
    detail: dict[str, Any] = field(default_factory=dict)
    audit: AuditIntent | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.code)

    @property
    def message_es(self) -> str:
        return ERROR_MESSAGES_ES.get(self.code, ERROR_MESSAGES_ES["internal_error"])


def unauthenticated(code: str = "authentication_required") -> FaroApiError:
    return FaroApiError(code, 401)


def forbidden(
    code: str = "forbidden", *, audit: AuditIntent | None = None, **detail: Any
) -> FaroApiError:
    return FaroApiError(code, 403, detail, audit)


def invalid(code: str = "validation_error", **detail: Any) -> FaroApiError:
    return FaroApiError(code, 422, detail)


def conflict(code: str, **detail: Any) -> FaroApiError:
    return FaroApiError(code, 409, detail)


def not_found(code: str = "not_found", **detail: Any) -> FaroApiError:
    return FaroApiError(code, 404, detail)


def precondition_required(code: str = "precondition_required") -> FaroApiError:
    return FaroApiError(code, 428)
