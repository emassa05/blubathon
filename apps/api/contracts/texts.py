"""Re-export de los textos visibles en español.

Los textos normativos viven en `packages/shared/texts.py`, que H1 publicó junto
con su versión generada para el frontend. `apps/**` no redacta copia visible:
la importa desde aquí.
"""

from __future__ import annotations

from packages.shared.texts import (
    AUDIT_SESSION_HINT_ES,
    AWAITING_PROFESSIONAL_REVIEW_ES,
    CONFLICTED_STATE_ES,
    DEFAULT_SUGGESTION_HINT_ES,
    EMERGENCY_LIMIT_ES,
    ERROR_MESSAGES_ES,
    INTENDED_USE_ES,
    OUTCOME_RESOLUTION_LABELS_ES,
    OUTCOME_VALUE_LABELS_ES,
    PREDICTION_ABSTENTION_ES,
    RECOMMENDATION_ABSTENTION_ES,
    SIMULATION_DISCLAIMER_ES,
)

__all__ = [
    "AUDIT_SESSION_HINT_ES",
    "AWAITING_PROFESSIONAL_REVIEW_ES",
    "CONFLICTED_STATE_ES",
    "DEFAULT_SUGGESTION_HINT_ES",
    "EMERGENCY_LIMIT_ES",
    "ERROR_MESSAGES_ES",
    "INTENDED_USE_ES",
    "OUTCOME_RESOLUTION_LABELS_ES",
    "OUTCOME_VALUE_LABELS_ES",
    "PREDICTION_ABSTENTION_ES",
    "RECOMMENDATION_ABSTENTION_ES",
    "SIMULATION_DISCLAIMER_ES",
]
