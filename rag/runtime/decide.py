"""The deterministic clinical runtime (SPEC 9.8, C29, C30, INV-26).

Zero LLM calls, zero embeddings, zero database access, zero network. The runtime
receives a categorical scenario and an explicit active catalogue, evaluates the
predicate of the set and of each strategy independently and fail-closed, and
returns at most three already-reviewed strategies with the citations of their
exact versions, or an abstention carrying an `AuthoringRequestIntent`.

It writes nothing. P2 persists the decision when it creates the episode, and a
later GET replays that stored envelope rather than calling here again.

Determinism is over domain content: the same scenario, catalogue version and
strategy versions produce the same ordered decision, on any machine, forever.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from packages.shared.constants import MAX_RUNTIME_STRATEGIES
from packages.shared.domain.rag import (
    AuthoringRequestIntent,
    CatalogVersion,
    RecommendationSetVersion,
    RuntimeDecision,
    RuntimeStrategyMatch,
    ScenarioV1,
    StrategyVersion,
)
from packages.shared.enums import (
    CatalogStatus,
    RecommendationAbstentionReason,
    RuntimeStatus,
    StrategyStatus,
)


@dataclass(frozen=True, slots=True)
class RuntimeCatalog:
    """One tenant catalogue and the exact versions it publishes.

    P2 selects the single active, effective catalogue and hands it over
    explicitly; the runtime never picks "the newest one" (SPEC 9.6).
    """

    catalog: CatalogVersion
    sets: tuple[RecommendationSetVersion, ...]
    strategies: Mapping[UUID, StrategyVersion]


@dataclass(frozen=True, slots=True)
class RuntimeInputs:
    """Everything the runtime may look at, and nothing else."""

    scenario: ScenarioV1
    scenario_hash: str
    as_of_at: datetime
    catalog: RuntimeCatalog | None = None
    readiness: RecommendationAbstentionReason | None = None


def _abstain(
    inputs: RuntimeInputs,
    reasons: Iterable[RecommendationAbstentionReason],
    *,
    catalog_version: str | None = None,
    corpus_version: str | None = None,
) -> RuntimeDecision:
    ordered = tuple(dict.fromkeys(reasons))
    intent = AuthoringRequestIntent(
        scenario_hash=inputs.scenario_hash,
        catalog_version=catalog_version,
        corpus_version=corpus_version,
        reasons=ordered,
    )
    return RuntimeDecision(
        status=RuntimeStatus.ABSTAINED,
        scenario_hash=inputs.scenario_hash,
        catalog_version=catalog_version,
        corpus_version=corpus_version,
        reasons=ordered,
        authoring_request_intent=intent,
    )


def _catalog_is_servable(catalog: CatalogVersion, as_of_at: datetime) -> bool:
    if catalog.status is not CatalogStatus.ACTIVE:
        return False
    if catalog.effective_from > as_of_at:
        return False
    return catalog.suspended_at is None or catalog.suspended_at > as_of_at


def _set_is_servable(version: RecommendationSetVersion, as_of_at: datetime) -> bool:
    if version.status is not CatalogStatus.ACTIVE:
        return False
    if version.effective_from > as_of_at:
        return False
    return version.suspended_at is None or version.suspended_at > as_of_at


def _eligible_sets(
    catalog: RuntimeCatalog, as_of_at: datetime
) -> tuple[RecommendationSetVersion, ...]:
    published = set(catalog.catalog.recommendation_set_version_ids)
    servable = [
        version
        for version in catalog.sets
        if version.recommendation_set_id in published and _set_is_servable(version, as_of_at)
    ]
    # SPEC 9.6: reviewed priority first, then the set version label. Nothing is
    # ranked by acceptance, recency or similarity in v0.3 (C32).
    servable.sort(
        key=lambda version: (version.reviewed_priority, version.recommendation_set_version)
    )
    return tuple(servable)


def decide(inputs: RuntimeInputs) -> RuntimeDecision:
    """Match a scenario against a precomputed catalogue, or abstain saying why."""

    if inputs.readiness is not None:
        return _abstain(inputs, (inputs.readiness,))
    if inputs.catalog is None:
        return _abstain(inputs, (RecommendationAbstentionReason.CATALOG_NOT_READY,))

    catalog = inputs.catalog
    catalog_version = catalog.catalog.catalog_version
    corpus_version = catalog.catalog.corpus_version

    if not _catalog_is_servable(catalog.catalog, inputs.as_of_at):
        reason = (
            RecommendationAbstentionReason.CATALOG_SUSPENDED
            if catalog.catalog.suspended_at is not None
            else RecommendationAbstentionReason.CATALOG_NOT_READY
        )
        return _abstain(inputs, (reason,))

    matches: list[RuntimeStrategyMatch] = []
    seen: set[UUID] = set()
    for version in _eligible_sets(catalog, inputs.as_of_at):
        if not version.applicability_predicate.matches(inputs.scenario):
            continue
        for position, strategy_version_id in enumerate(version.ordered_strategy_version_ids):
            strategy = catalog.strategies.get(strategy_version_id)
            if strategy is None:
                # An active set naming a version the runtime does not hold is an
                # inconsistent catalogue. It fails closed rather than serving
                # part of a set (SPEC 9.6).
                return _abstain(
                    inputs,
                    (RecommendationAbstentionReason.CATALOG_NOT_READY,),
                    catalog_version=catalog_version,
                    corpus_version=corpus_version,
                )
            if strategy.status is not StrategyStatus.ACTIVE:
                return _abstain(
                    inputs,
                    (RecommendationAbstentionReason.CATALOG_SUSPENDED,),
                    catalog_version=catalog_version,
                    corpus_version=corpus_version,
                )
            if strategy.effective_from > inputs.as_of_at:
                continue
            # Evaluated again, independently of the set that carried it.
            if not strategy.applicability_predicate.matches(inputs.scenario):
                continue
            if strategy_version_id in seen:
                continue
            seen.add(strategy_version_id)
            matches.append(
                RuntimeStrategyMatch(
                    strategy_version_id=strategy_version_id,
                    recommendation_set_id=version.recommendation_set_id,
                    recommendation_set_version=version.recommendation_set_version,
                    reviewed_priority=version.reviewed_priority,
                    position_in_set=position,
                    action_text_es=strategy.action_text_es,
                    citations=strategy.citations,
                )
            )
            if len(matches) == MAX_RUNTIME_STRATEGIES:
                break
        if len(matches) == MAX_RUNTIME_STRATEGIES:
            break

    if not matches:
        return _abstain(
            inputs,
            (RecommendationAbstentionReason.NO_APPROVED_MATCH,),
            catalog_version=catalog_version,
            corpus_version=corpus_version,
        )

    return RuntimeDecision(
        status=RuntimeStatus.MATCHED,
        scenario_hash=inputs.scenario_hash,
        catalog_version=catalog_version,
        corpus_version=corpus_version,
        matches=tuple(matches),
    )
