"""Runtime de recomendación fixture (sustituye `rag/runtime` hasta H1).

Este stub **no** hace RAG: no indexa, no recupera, no usa BM25, embeddings, RRF
ni verifica citas contra hashes. Todo eso es autoría y pertenece a P1.6/P1.7.

Lo único que hace es evaluar fail-closed el `ScenarioPredicate` del set y de cada
estrategia sobre el catálogo precomputado que P2 le entrega, respetando el orden
revisado y el tope de `MAX_RUNTIME_STRATEGIES`. Es el mínimo necesario para que
el inbox profesional, las reviews y las ejecuciones tengan algo real que operar
mientras P1 publica el runtime normativo.
"""

from __future__ import annotations

from typing import Any

from apps.api.contracts.constants import MAX_RUNTIME_STRATEGIES
from apps.api.contracts.enums import RuntimeStatus
from apps.api.ports.rag import CatalogSnapshot, RuntimeDecision, RuntimeStrategy


def _as_set(value: Any) -> set[str]:
    if value is None:
        return set()
    return {str(item) for item in value}


def _matches(predicate: dict[str, Any], scenario: dict[str, Any]) -> bool:
    """SPEC 9.6. Fail-closed: cualquier campo o tag desconocido no calza."""
    field_values: dict[str, str] = dict(scenario.get("field_values") or {})
    context_tags = _as_set(scenario.get("context_tags"))
    profile_tags = _as_set(scenario.get("profile_tags"))
    contraindication_tags = _as_set(scenario.get("contraindication_tags"))

    for code, allowed in (predicate.get("required_field_values") or {}).items():
        if code not in field_values or field_values[code] not in _as_set(allowed):
            return False
    for code, forbidden in (predicate.get("excluded_field_values") or {}).items():
        if code in field_values and field_values[code] in _as_set(forbidden):
            return False
    if not _as_set(predicate.get("required_context_tags")) <= context_tags:
        return False
    if _as_set(predicate.get("excluded_context_tags")) & context_tags:
        return False
    if not _as_set(predicate.get("required_profile_tags")) <= profile_tags:
        return False
    return not _as_set(predicate.get("contraindication_tags")) & contraindication_tags


class MockRagRuntime:
    def recommend(
        self,
        *,
        tenant_id: str,
        scenario: dict[str, Any],
        catalog: CatalogSnapshot,
        as_of_at: str,
    ) -> RuntimeDecision:
        if catalog.tenant_id != tenant_id:
            # Scope revalidado dentro del runtime (SPEC 9.6).
            return RuntimeDecision(
                status=RuntimeStatus.ABSTAINED.value,
                abstention_reasons=("catalog_scope_mismatch",),
            )

        selected: list[RuntimeStrategy] = []
        ordered_sets = sorted(
            catalog.sets,
            key=lambda item: (item.reviewed_priority, item.recommendation_set_version),
        )
        for catalog_set in ordered_sets:
            if not _matches(catalog_set.applicability_predicate, scenario):
                continue
            for strategy in catalog_set.strategies:
                # SPEC 9.6: set y estrategia se evalúan de nuevo por separado.
                if not _matches(strategy.applicability_predicate, scenario):
                    continue
                if any(
                    chosen.strategy_version_id == strategy.strategy_version_id
                    for chosen in selected
                ):
                    continue
                selected.append(strategy)
                if len(selected) == MAX_RUNTIME_STRATEGIES:
                    break
            if len(selected) == MAX_RUNTIME_STRATEGIES:
                break

        if not selected:
            # SPEC 9.8: un escenario no cubierto se abstiene y pide autoría.
            return RuntimeDecision(
                status=RuntimeStatus.ABSTAINED.value,
                abstention_reasons=("no_approved_match",),
                authoring_request_intent=True,
                intent_reason="no_approved_match",
            )
        return RuntimeDecision(status=RuntimeStatus.MATCHED.value, strategies=tuple(selected))
