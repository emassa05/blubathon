"""`rag.runtime` detrás del puerto del runtime determinista (SPEC 9.6-9.8).

El puerto pide `recommend` y P1 publica `decide(RuntimeInputs) -> RuntimeDecision`
con `RuntimeCatalog`. El adaptador arma esas entradas: el `CatalogSnapshot` que
P2 ya seleccionó identifica el catálogo, y el store devuelve las filas completas
-estado, vigencia, hash- que los modelos del contrato exigen y el snapshot del
puerto no transporta.

El runtime sigue siendo puro: no lee la base, no llama a un LLM y no escribe. Lo
que lee la base es este adaptador, antes de invocarlo.
"""

from __future__ import annotations

from typing import Any

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import keyed_scenario_hash, parse_timestamp
from apps.api.ports.rag import (
    CatalogSnapshot,
    RuntimeCitation,
    RuntimeDecision,
    RuntimeStrategy,
)
from apps.api.store import history
from apps.api.store.db import Database
from packages.shared.constants import SCENARIO_SCHEMA_VERSION
from packages.shared.domain.rag import ScenarioV1
from packages.shared.enums import RecommendationAbstentionReason, RuntimeStatus
from rag.runtime import RuntimeCatalog, RuntimeInputs, decide


class P1RagRuntime:
    def __init__(self, *, database: Database, secret: bytes) -> None:
        self._database = database
        self._secret = secret

    def recommend(
        self,
        *,
        tenant_id: str,
        scenario: dict[str, Any],
        catalog: CatalogSnapshot,
        as_of_at: str,
    ) -> RuntimeDecision:
        if catalog.tenant_id != tenant_id:
            # SPEC 9.6: el scope se revalida antes de mirar el catálogo.
            return RuntimeDecision(
                status=RuntimeStatus.ABSTAINED.value,
                abstention_reasons=(RecommendationAbstentionReason.CATALOG_NOT_READY.value,),
                authoring_request_intent=False,
                intent_reason=None,
            )

        payload = ScenarioV1.model_validate({"schema_version": SCENARIO_SCHEMA_VERSION, **scenario})
        scenario_hash = keyed_scenario_hash(
            self._secret, payload.schema_version, payload.canonical_payload()
        )
        decision = decide(
            RuntimeInputs(
                scenario=payload,
                scenario_hash=scenario_hash,
                as_of_at=parse_timestamp(as_of_at),
                catalog=self._catalog(tenant_id=tenant_id, catalog=catalog),
            )
        )
        if decision.status is not RuntimeStatus.MATCHED:
            return RuntimeDecision(
                status=RuntimeStatus.ABSTAINED.value,
                abstention_reasons=tuple(reason.value for reason in decision.reasons),
                authoring_request_intent=decision.authoring_request_intent is not None,
                intent_reason=(None if not decision.reasons else decision.reasons[0].value),
            )

        by_id = {
            strategy.strategy_version_id: strategy
            for catalog_set in catalog.sets
            for strategy in catalog_set.strategies
        }
        strategies = tuple(
            _strategy(match, by_id.get(str(match.strategy_version_id)))
            for match in decision.matches
        )
        return RuntimeDecision(status=RuntimeStatus.MATCHED.value, strategies=strategies)

    def _catalog(self, *, tenant_id: str, catalog: CatalogSnapshot) -> RuntimeCatalog | None:
        connection = self._database.connection
        catalog_row = history.catalog_version_row(
            connection, tenant_id=tenant_id, catalog_version=catalog.catalog_version
        )
        if catalog_row is None:
            return None
        version = translate.catalog_version(catalog_row)
        set_ids = tuple(str(item) for item in version.recommendation_set_version_ids)
        sets = tuple(
            translate.recommendation_set_version(row)
            for row in history.recommendation_set_rows(
                connection, recommendation_set_version_ids=set_ids
            )
        )
        strategy_ids = tuple(
            str(item) for version_set in sets for item in version_set.ordered_strategy_version_ids
        )
        citations: dict[str, list[Any]] = {}
        for row in history.citations_for_strategies(connection, strategy_version_ids=strategy_ids):
            citations.setdefault(str(row["strategy_version_id"]), []).append(
                translate.strategy_citation(row)
            )
        strategies = {}
        for row in history.strategy_version_rows(connection, strategy_version_ids=strategy_ids):
            strategy = translate.strategy_version(
                row, tuple(citations.get(str(row["strategy_version_id"]), ()))
            )
            strategies[strategy.strategy_version_id] = strategy
        return RuntimeCatalog(catalog=version, sets=sets, strategies=strategies)


def _strategy(match: Any, precomputed: RuntimeStrategy | None) -> RuntimeStrategy:
    """El runtime devuelve texto y citas; los roles vienen del catálogo de P2.

    `RuntimeStrategyMatch` no lleva `required_approver_role` ni
    `allowed_executor_roles` porque no son parte de la decisión, sino de quién
    puede aprobar y aplicar lo decidido (SPEC 10.2, 10.3).
    """
    return RuntimeStrategy(
        strategy_version_id=str(match.strategy_version_id),
        action_text_es=match.action_text_es,
        required_approver_role=("" if precomputed is None else precomputed.required_approver_role),
        allowed_executor_roles=(() if precomputed is None else precomputed.allowed_executor_roles),
        applicability_predicate={} if precomputed is None else precomputed.applicability_predicate,
        citations=tuple(
            RuntimeCitation(
                citation_id=str(citation.citation_id),
                claim_id=str(citation.claim_id),
                locator=citation.locator,
                quoted_text=citation.quoted_text,
                canonical_url=str(citation.canonical_url),
            )
            for citation in match.citations
        ),
    )
