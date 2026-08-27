"""Puertos hacia el dominio puro de P1.

P2 nunca importa `ml/**` ni `rag/**` directamente. Toda dependencia pasa por
estos protocolos, así que sustituir un mock por la façade real de P1 es cambiar
un adaptador (`apps/api/adapters`), no rediseñar servicios, store o UI.

Ningún puerto calcula: declara la forma del resultado que P1 devuelve.
"""

from __future__ import annotations

from apps.api.ports.defaults import AuditAssignment, DefaultDecision, DefaultsPort
from apps.api.ports.form import (
    FormPlan,
    FormPort,
    PlannedQuestion,
)
from apps.api.ports.prediction import PredictionPort, TrackOutput

__all__ = [
    "AuditAssignment",
    "DefaultDecision",
    "DefaultsPort",
    "FormPlan",
    "FormPort",
    "PlannedQuestion",
    "PredictionPort",
    "TrackOutput",
]
