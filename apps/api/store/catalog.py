"""Selección y disponibilidad del catálogo antes del runtime (SPEC 9.6).

P2 deriva una razón única con la precedencia del SPEC y se la pasa al runtime;
`clinical_review_unavailable` nunca se reduce a `catalog_not_ready`, y un estado
suspendido o ambiguo falla cerrado.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from apps.api.contracts.enums import CatalogReadiness, CatalogStatus, DocumentStatus, StrategyStatus
from apps.api.ports.rag import CatalogSet, CatalogSnapshot, RuntimeCitation, RuntimeStrategy
from apps.api.store.json_columns import load_dict, load_list


@dataclass(frozen=True, slots=True)
class CatalogAvailabilityResult:
    reason: CatalogReadiness
    catalog_version: str | None
    corpus_version: str | None

    @property
    def ready(self) -> bool:
        return self.reason is CatalogReadiness.READY


def _active_corpus(connection: sqlite3.Connection, cutoff: str) -> str | None:
    row = connection.execute(
        "SELECT corpus_version FROM corpus_versions"
        " WHERE status = 'active' AND effective_from <= ?"
        " AND suspended_at IS NULL AND retired_at IS NULL"
        " ORDER BY effective_from DESC LIMIT 1",
        (cutoff,),
    ).fetchone()
    return None if row is None else row["corpus_version"]


def derive_availability(
    connection: sqlite3.Connection, *, tenant_id: str, cutoff: str
) -> CatalogAvailabilityResult:
    corpus_version = _active_corpus(connection, cutoff)
    if corpus_version is None:
        return CatalogAvailabilityResult(CatalogReadiness.CORPUS_NOT_READY, None, None)

    active_catalogs = connection.execute(
        "SELECT catalog_version, corpus_version FROM catalog_versions"
        " WHERE tenant_id = ? AND status = 'active' AND effective_from <= ?"
        " AND suspended_at IS NULL AND retired_at IS NULL"
        " ORDER BY effective_from DESC, catalog_version",
        (tenant_id, cutoff),
    ).fetchall()

    if not active_catalogs:
        # Una versión revisable bloqueada solo por review clínica tiene su propia
        # razón: no se confunde con "no hay catálogo".
        awaiting_clinical = connection.execute(
            "SELECT 1 FROM strategy_versions WHERE status = ?"
            " AND evidence_review_id IS NOT NULL AND clinical_review_id IS NULL LIMIT 1",
            (StrategyStatus.EVIDENCE_REVIEWED.value,),
        ).fetchone()
        if awaiting_clinical is not None:
            return CatalogAvailabilityResult(
                CatalogReadiness.CLINICAL_REVIEW_UNAVAILABLE, None, corpus_version
            )
        suspended = connection.execute(
            "SELECT 1 FROM catalog_versions WHERE tenant_id = ? AND status = ? LIMIT 1",
            (tenant_id, CatalogStatus.SUSPENDED.value),
        ).fetchone()
        if suspended is not None:
            return CatalogAvailabilityResult(
                CatalogReadiness.CATALOG_SUSPENDED, None, corpus_version
            )
        return CatalogAvailabilityResult(CatalogReadiness.CATALOG_NOT_READY, None, corpus_version)

    if len(active_catalogs) > 1:
        return CatalogAvailabilityResult(CatalogReadiness.CATALOG_AMBIGUOUS, None, corpus_version)

    chosen = active_catalogs[0]
    # Una dependencia antes activa y ahora suspendida bloquea nuevas instancias.
    suspended_dependency = connection.execute(
        "SELECT 1 FROM recommendation_set_versions"
        " WHERE status = ? AND recommendation_set_version_id IN"
        " (SELECT json_each.value FROM catalog_versions, json_each("
        "  catalog_versions.recommendation_set_version_ids)"
        "  WHERE catalog_versions.catalog_version = ?) LIMIT 1",
        (CatalogStatus.SUSPENDED.value, chosen["catalog_version"]),
    ).fetchone()
    if suspended_dependency is not None:
        return CatalogAvailabilityResult(CatalogReadiness.CATALOG_SUSPENDED, None, corpus_version)
    return CatalogAvailabilityResult(
        CatalogReadiness.READY, chosen["catalog_version"], chosen["corpus_version"]
    )


def load_snapshot(
    connection: sqlite3.Connection, *, tenant_id: str, catalog_version: str, cutoff: str
) -> CatalogSnapshot:
    """Catálogo precomputado que se entrega al runtime puro."""
    catalog = connection.execute(
        "SELECT * FROM catalog_versions WHERE catalog_version = ? AND tenant_id = ?",
        (catalog_version, tenant_id),
    ).fetchone()
    if catalog is None:
        return CatalogSnapshot(catalog_version, None, tenant_id, ())

    set_ids = load_list(catalog["recommendation_set_version_ids"])
    sets: list[CatalogSet] = []
    for set_version_id in set_ids:
        set_row = connection.execute(
            "SELECT * FROM recommendation_set_versions"
            " WHERE recommendation_set_version_id = ? AND status = ?"
            " AND effective_from <= ? AND suspended_at IS NULL",
            (set_version_id, CatalogStatus.ACTIVE.value, cutoff),
        ).fetchone()
        if set_row is None:
            continue
        strategies: list[RuntimeStrategy] = []
        for strategy_version_id in load_list(set_row["ordered_strategy_version_ids"]):
            strategy = _load_strategy(connection, strategy_version_id, cutoff)
            if strategy is not None:
                strategies.append(strategy)
        sets.append(
            CatalogSet(
                recommendation_set_version_id=set_row["recommendation_set_version_id"],
                recommendation_set_version=set_row["recommendation_set_version"],
                reviewed_priority=int(set_row["reviewed_priority"]),
                applicability_predicate=_predicate(set_row["applicability_predicate"]),
                strategies=tuple(strategies),
            )
        )
    return CatalogSnapshot(
        catalog_version=catalog_version,
        corpus_version=catalog["corpus_version"],
        tenant_id=tenant_id,
        sets=tuple(sets),
    )


def _predicate(raw: str) -> dict[str, object]:
    return load_dict(raw)


def _load_strategy(
    connection: sqlite3.Connection, strategy_version_id: str, cutoff: str
) -> RuntimeStrategy | None:
    row = connection.execute(
        "SELECT * FROM strategy_versions WHERE strategy_version_id = ? AND status = ?"
        " AND effective_from <= ? AND suspended_at IS NULL",
        (strategy_version_id, StrategyStatus.ACTIVE.value, cutoff),
    ).fetchone()
    if row is None:
        return None
    citations = connection.execute(
        "SELECT * FROM strategy_citations WHERE strategy_version_id = ?"
        " ORDER BY claim_id, citation_id",
        (strategy_version_id,),
    ).fetchall()
    return RuntimeStrategy(
        strategy_version_id=row["strategy_version_id"],
        action_text_es=row["action_text_es"],
        required_approver_role=row["required_approver_role"],
        allowed_executor_roles=tuple(load_list(row["allowed_executor_roles"])),
        applicability_predicate=_predicate(row["applicability_predicate"]),
        citations=tuple(
            RuntimeCitation(
                citation_id=citation["citation_id"],
                claim_id=citation["claim_id"],
                locator=citation["locator"],
                quoted_text=citation["quoted_text"],
                canonical_url=citation["canonical_url"],
            )
            for citation in citations
        ),
    )


def dependencies_active(
    connection: sqlite3.Connection,
    *,
    strategy_version_id: str,
    catalog_version: str | None,
    cutoff: str,
) -> bool:
    """SPEC 10.2: estrategia, set, catálogo y fuentes exactas siguen activos."""
    if catalog_version is None:
        return False
    strategy = connection.execute(
        "SELECT status, suspended_at, corpus_version FROM strategy_versions"
        " WHERE strategy_version_id = ?",
        (strategy_version_id,),
    ).fetchone()
    if strategy is None or strategy["status"] != StrategyStatus.ACTIVE.value:
        return False
    if strategy["suspended_at"] is not None:
        return False
    catalog = connection.execute(
        "SELECT status, suspended_at, retired_at, corpus_version FROM catalog_versions"
        " WHERE catalog_version = ?",
        (catalog_version,),
    ).fetchone()
    if catalog is None or catalog["status"] != CatalogStatus.ACTIVE.value:
        return False
    if catalog["suspended_at"] is not None or catalog["retired_at"] is not None:
        return False
    corpus = connection.execute(
        "SELECT status, suspended_at, retired_at FROM corpus_versions WHERE corpus_version = ?",
        (catalog["corpus_version"],),
    ).fetchone()
    if corpus is None or corpus["status"] != DocumentStatus.ACTIVE.value:
        return False
    if corpus["suspended_at"] is not None or corpus["retired_at"] is not None:
        return False
    containing_set = connection.execute(
        "SELECT status, suspended_at FROM recommendation_set_versions"
        " WHERE recommendation_set_version_id IN"
        " (SELECT json_each.value FROM catalog_versions, json_each("
        "  catalog_versions.recommendation_set_version_ids)"
        "  WHERE catalog_versions.catalog_version = ?)"
        " AND EXISTS (SELECT 1 FROM json_each("
        "     recommendation_set_versions.ordered_strategy_version_ids)"
        "     WHERE json_each.value = ?)",
        (catalog_version, strategy_version_id),
    ).fetchall()
    if not containing_set:
        return False
    return all(
        row["status"] == CatalogStatus.ACTIVE.value and row["suspended_at"] is None
        for row in containing_set
    )
