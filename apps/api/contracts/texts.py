"""Textos normativos visibles en español de Chile.

PROVISIONAL - PUERTO HACIA P1 (`packages/shared/texts.py`).

El límite de emergencia de `SPEC 13.2` y `SPEC 2.27` es obligatorio en entrada,
abstención, resultados y recomendaciones: la interfaz nunca sugiere esperar una
alerta de Faro ante peligro inmediato.
"""

from __future__ import annotations

EMERGENCY_NOTICE_ES = (
    "Faro no monitorea emergencias y no te avisará si algo urgente ocurre. "
    "Ante peligro inmediato sigue de inmediato los protocolos de emergencia o "
    "resguardo de tu comunidad; no esperes una alerta de esta aplicación."
)

ABSTENTION_NOTICE_ES = (
    "Faro no tiene información suficiente para estimar esto y por eso se abstiene. "
    "Una abstención no es un error ni significa que todo esté bien."
)

SIMULATION_NOTICE_ES = (
    "Este número viene de una simulación diseñada, no de datos de una persona "
    "real. No es una probabilidad clínica."
)

PENDING_REVIEW_NOTICE_ES = (
    "Estas sugerencias esperan revisión de un profesional. Todavía no hay nada "
    "aprobado para aplicar."
)

DEFAULT_SUGGESTION_NOTICE_ES = (
    "Esto es una sugerencia basada en tu propio historial. Si no la tocas, no se guarda nada."
)

CONFLICT_NOTICE_ES = (
    "Hay reportes incompatibles para esta ventana. El caso queda marcado como "
    "conflicto y no se usa para estadística."
)

ABSTENTION_REASONS_ES: dict[str, str] = {
    "insufficient_verified_outcomes": (
        "Aún no hay suficientes resultados verificados de esta persona."
    ),
    "care_mode_history_unavailable": "Falta el modo de cuidado histórico del episodio.",
    "unresolved_conflict": "Hay un conflicto sin resolver en la ventana usada.",
    "not_trainable_single_class": "El modelo no es entrenable con una sola clase observada.",
    "real_subject_rejected_by_simulation_track": (
        "El modelo de simulación no se aplica a personas reales."
    ),
    "simulation_fixture_unavailable": "No hay un escenario de simulación para esta persona.",
    "corpus_not_ready": "Todavía no hay un corpus autorizado y versionado.",
    "clinical_review_unavailable": "Falta una revisión clínica autorizada.",
    "catalog_suspended": "Una dependencia del catálogo está suspendida.",
    "catalog_ambiguous": "Hay más de un catálogo activo vigente.",
    "catalog_not_ready": "No hay un catálogo activo para esta organización.",
    "no_approved_match": "Ninguna estrategia aprobada calza con este escenario.",
    "scenario_unavailable_conflict": "El escenario tiene valores en conflicto.",
    "scenario_unavailable_profile": "Falta el perfil versionado de la persona.",
    "catalog_scope_mismatch": "El catálogo consultado no pertenece a esta organización.",
    "target_definition_unavailable": (
        "No hay una definición de objetivo activa para registrar resultados reales."
    ),
    "target_definition_ambiguous": (
        "Hay más de una definición de objetivo vigente; el sistema no elige por su cuenta."
    ),
}

OUTCOME_REQUEST_STATUS_ES: dict[str, str] = {
    "open": "Esperando tu respuesta",
    "reported": "Respondido",
    "conflicted": "Con reportes incompatibles",
    "missing": "Sin respuesta dentro del plazo",
}

RESOLUTION_STATUS_ES: dict[str, str] = {
    "pending": "Sin resolver",
    "yes": "Ocurrió",
    "no": "No ocurrió",
    "unknown": "No se pudo saber",
    "conflicted": "En conflicto",
}
