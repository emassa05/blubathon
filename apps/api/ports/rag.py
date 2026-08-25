"""Puerto del runtime determinista de recomendación (SPEC 9.6-9.8; P1.7).

El runtime es una función pura: recibe el escenario y el catálogo precomputado
que P2 ya seleccionó, y devuelve una decisión. No consulta la base clínica, no
llama a un LLM y no escribe filas. La disponibilidad del catálogo (SPEC 9.6) la
deriva P2 **antes** de llamar aquí.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RuntimeCitation:
    citation_id: str
    claim_id: str
    locator: str
    quoted_text: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class RuntimeStrategy:
    strategy_version_id: str
    action_text_es: str
    required_approver_role: str
    allowed_executor_roles: tuple[str, ...]
    applicability_predicate: dict[str, Any] = field(default_factory=dict)
    citations: tuple[RuntimeCitation, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogSet:
    recommendation_set_version_id: str
    recommendation_set_version: str
    reviewed_priority: int
    applicability_predicate: dict[str, Any]
    strategies: tuple[RuntimeStrategy, ...]


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """Catálogo activo ya seleccionado por P2, con scope y estado validados."""

    catalog_version: str
    corpus_version: str | None
    tenant_id: str
    sets: tuple[CatalogSet, ...]


@dataclass(frozen=True, slots=True)
class RuntimeDecision:
    """`authoring_request_intent` es intención: P2 decide crear y deduplicar."""

    status: str
    strategies: tuple[RuntimeStrategy, ...] = ()
    abstention_reasons: tuple[str, ...] = ()
    authoring_request_intent: bool = False
    intent_reason: str | None = None


class RagRuntimePort(Protocol):
    def recommend(
        self,
        *,
        tenant_id: str,
        scenario: dict[str, Any],
        catalog: CatalogSnapshot,
        as_of_at: str,
    ) -> RuntimeDecision: ...
