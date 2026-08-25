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
    ScenarioResult,
)
from apps.api.ports.prediction import PredictionPort, TrackOutput
from apps.api.ports.rag import (
    CatalogSet,
    CatalogSnapshot,
    RagRuntimePort,
    RuntimeCitation,
    RuntimeDecision,
    RuntimeStrategy,
)

__all__ = [
    "AuditAssignment",
    "CatalogSet",
    "CatalogSnapshot",
    "DefaultDecision",
    "DefaultsPort",
    "FormPlan",
    "FormPort",
    "PlannedQuestion",
    "PredictionPort",
    "RagRuntimePort",
    "RuntimeCitation",
    "RuntimeDecision",
    "RuntimeStrategy",
    "ScenarioResult",
    "TrackOutput",
]
