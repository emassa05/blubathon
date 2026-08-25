"""The deterministic runtime: match, cap, order, or abstain (SPEC 9.8)."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.shared.constants import MAX_RUNTIME_STRATEGIES
from packages.shared.domain.rag import ScenarioPredicate, resolve_catalog_readiness
from packages.shared.enums import (
    CatalogStatus,
    FieldCode,
    RecommendationAbstentionReason,
    RuntimeStatus,
    StrategyStatus,
)
from rag.runtime import RuntimeCatalog, RuntimeInputs, decide
from tests.p1 import rag_factories as rf
from tests.p1.factories import ident

SLEEP_SCENARIO = rf.scenario(sleep_quality="interrupted", alertness="high")
GI_SCENARIO = rf.scenario(gi_status="constipation")

SLEEP_PREDICATE = ScenarioPredicate(
    required_field_values={FieldCode.SLEEP_QUALITY: ("interrupted", "sleep_onset_difficulty")}
)
GI_PREDICATE = ScenarioPredicate(required_field_values={FieldCode.GI_STATUS: ("constipation",)})


def _strategy(label: str, build, *, quote, action, claim, predicate, **overrides):
    return rf.strategy(
        label,
        build=build,
        quote=quote,
        action_text=action,
        claim_text=claim,
        predicate=predicate,
        evidence_review_id=ident(f"review:{label}-evidence"),
        clinical_review_id=ident(f"review:{label}-clinical"),
        **overrides,
    )


def _catalog(build, *sets, status=CatalogStatus.ACTIVE, suspended_at=None):
    return rf.catalog(
        "demo",
        build=build,
        set_ids=tuple(version.recommendation_set_id for version in sets),
        status=status,
        activation_review_id=ident("review:catalog-activation"),
        suspended_at=suspended_at,
    )


def _inputs(build, catalog, sets, strategies, *, scenario=SLEEP_SCENARIO, readiness=None):
    return RuntimeInputs(
        scenario=scenario,
        scenario_hash="fixture-scenario-hash",
        as_of_at=rf.NOW,
        catalog=RuntimeCatalog(
            catalog=catalog,
            sets=sets,
            strategies={item.strategy_version_id: item for item in strategies},
        ),
        readiness=readiness,
    )


def _one_set_catalog(build, *, predicate=SLEEP_PREDICATE, strategy_predicate=SLEEP_PREDICATE):
    strategy = _strategy(
        "sleep",
        build,
        quote=rf.SLEEP_QUOTE,
        action=rf.ACTION_TEXT_SLEEP,
        claim=rf.CLAIM_TEXT_SLEEP,
        predicate=strategy_predicate,
    )
    version = rf.recommendation_set(
        "sleep",
        strategy_version_ids=(strategy.strategy_version_id,),
        predicate=predicate,
        clinical_review_id=ident("review:set-clinical"),
    )
    return _catalog(build, version), (version,), (strategy,)


class TestMatching:
    def test_a_matching_scenario_gets_the_reviewed_text_and_its_citations(self) -> None:
        build = rf.fixture_build()
        catalog, sets, strategies = _one_set_catalog(build)
        decision = decide(_inputs(build, catalog, sets, strategies))
        assert decision.status is RuntimeStatus.MATCHED
        assert decision.matches[0].action_text_es == rf.ACTION_TEXT_SLEEP
        assert decision.matches[0].citations[0].quoted_text == rf.SLEEP_QUOTE
        assert decision.catalog_version == catalog.catalog_version
        assert decision.corpus_version == build.corpus.corpus_version

    def test_the_same_scenario_and_versions_return_the_same_decision(self) -> None:
        build = rf.fixture_build()
        catalog, sets, strategies = _one_set_catalog(build)
        first = decide(_inputs(build, catalog, sets, strategies))
        second = decide(_inputs(build, catalog, sets, strategies))
        assert first == second

    def test_a_strategy_predicate_is_evaluated_again_inside_a_matching_set(self) -> None:
        build = rf.fixture_build()
        # The set matches the scenario; the strategy it carries does not.
        catalog, sets, strategies = _one_set_catalog(
            build, predicate=SLEEP_PREDICATE, strategy_predicate=GI_PREDICATE
        )
        decision = decide(_inputs(build, catalog, sets, strategies))
        assert decision.status is RuntimeStatus.ABSTAINED
        assert decision.reasons == (RecommendationAbstentionReason.NO_APPROVED_MATCH,)

    def test_a_contraindicated_scenario_never_matches(self) -> None:
        build = rf.fixture_build()
        guarded = ScenarioPredicate(
            required_field_values={FieldCode.SLEEP_QUALITY: ("interrupted",)},
            contraindication_tags=("no_sensory_reduction",),
        )
        catalog, sets, strategies = _one_set_catalog(
            build, predicate=guarded, strategy_predicate=guarded
        )
        scenario = rf.scenario(sleep_quality="interrupted").model_copy(
            update={"contraindication_tags": ("no_sensory_reduction",)}
        )
        decision = decide(_inputs(build, catalog, sets, strategies, scenario=scenario))
        assert decision.status is RuntimeStatus.ABSTAINED

    def test_at_most_three_strategies_are_returned(self) -> None:
        build = rf.fixture_build()
        strategies = tuple(
            _strategy(
                f"sleep-{index}",
                build,
                quote=rf.SLEEP_QUOTE,
                action=rf.ACTION_TEXT_SLEEP,
                claim=rf.CLAIM_TEXT_SLEEP,
                predicate=SLEEP_PREDICATE,
            )
            for index in range(5)
        )
        version = rf.recommendation_set(
            "many",
            strategy_version_ids=tuple(item.strategy_version_id for item in strategies),
            predicate=SLEEP_PREDICATE,
            clinical_review_id=ident("review:set-clinical"),
        )
        catalog = _catalog(build, version)
        decision = decide(_inputs(build, catalog, (version,), strategies))
        assert len(decision.matches) == MAX_RUNTIME_STRATEGIES

    def test_sets_are_ordered_by_reviewed_priority_then_version(self) -> None:
        build = rf.fixture_build()
        sleep = _strategy(
            "sleep",
            build,
            quote=rf.SLEEP_QUOTE,
            action=rf.ACTION_TEXT_SLEEP,
            claim=rf.CLAIM_TEXT_SLEEP,
            predicate=ScenarioPredicate(),
        )
        gi = _strategy(
            "gi",
            build,
            quote=rf.GI_QUOTE,
            action=rf.ACTION_TEXT_GI,
            claim=rf.CLAIM_TEXT_GI,
            predicate=ScenarioPredicate(),
        )
        low = rf.recommendation_set(
            "low",
            strategy_version_ids=(gi.strategy_version_id,),
            predicate=ScenarioPredicate(),
            reviewed_priority=5,
            clinical_review_id=ident("review:set-clinical"),
        )
        high = rf.recommendation_set(
            "high",
            strategy_version_ids=(sleep.strategy_version_id,),
            predicate=ScenarioPredicate(),
            reviewed_priority=1,
            clinical_review_id=ident("review:set-clinical"),
        )
        catalog = _catalog(build, low, high)
        decision = decide(_inputs(build, catalog, (low, high), (sleep, gi)))
        assert [match.strategy_version_id for match in decision.matches] == [
            sleep.strategy_version_id,
            gi.strategy_version_id,
        ]


class TestAbstention:
    def test_a_blocked_corpus_abstains_with_corpus_not_ready(self) -> None:
        build = rf.fixture_build()
        readiness = resolve_catalog_readiness(
            corpus_available=False,
            blocked_only_by_clinical_review=False,
            dependency_suspended=False,
            active_catalog_count=0,
        )
        decision = decide(
            RuntimeInputs(
                scenario=SLEEP_SCENARIO,
                scenario_hash="fixture-scenario-hash",
                as_of_at=rf.NOW,
                readiness=readiness,
            )
        )
        assert decision.status is RuntimeStatus.ABSTAINED
        assert decision.reasons == (RecommendationAbstentionReason.CORPUS_NOT_READY,)
        assert decision.authoring_request_intent is not None
        assert decision.catalog_version is None
        assert build.manifest.retrieval_mode.value == "lexical_only"

    def test_a_missing_clinical_reviewer_never_collapses_into_catalog_not_ready(self) -> None:
        readiness = resolve_catalog_readiness(
            corpus_available=True,
            blocked_only_by_clinical_review=True,
            dependency_suspended=False,
            active_catalog_count=0,
        )
        decision = decide(
            RuntimeInputs(
                scenario=SLEEP_SCENARIO,
                scenario_hash="fixture-scenario-hash",
                as_of_at=rf.NOW,
                readiness=readiness,
            )
        )
        assert decision.reasons == (RecommendationAbstentionReason.CLINICAL_REVIEW_UNAVAILABLE,)

    def test_an_ambiguous_catalogue_fails_closed(self) -> None:
        readiness = resolve_catalog_readiness(
            corpus_available=True,
            blocked_only_by_clinical_review=False,
            dependency_suspended=False,
            active_catalog_count=2,
        )
        assert readiness is RecommendationAbstentionReason.CATALOG_AMBIGUOUS

    def test_a_suspended_catalogue_abstains_rather_than_serving_history(self) -> None:
        build = rf.fixture_build()
        _, sets, strategies = _one_set_catalog(build)
        suspended = _catalog(
            build,
            *sets,
            status=CatalogStatus.SUSPENDED,
            suspended_at=datetime(2026, 8, 22, tzinfo=UTC),
        )
        decision = decide(_inputs(build, suspended, sets, strategies))
        assert decision.reasons == (RecommendationAbstentionReason.CATALOG_SUSPENDED,)

    def test_a_suspended_strategy_inside_an_active_set_fails_closed(self) -> None:
        build = rf.fixture_build()
        catalog, sets, strategies = _one_set_catalog(build)
        suspended = strategies[0].model_copy(update={"status": StrategyStatus.SUSPENDED})
        decision = decide(_inputs(build, catalog, sets, (suspended,)))
        assert decision.reasons == (RecommendationAbstentionReason.CATALOG_SUSPENDED,)

    def test_a_set_naming_an_unknown_version_fails_closed(self) -> None:
        build = rf.fixture_build()
        catalog, sets, _ = _one_set_catalog(build)
        decision = decide(_inputs(build, catalog, sets, ()))
        assert decision.reasons == (RecommendationAbstentionReason.CATALOG_NOT_READY,)

    def test_an_abstention_always_carries_an_authoring_request_intent(self) -> None:
        build = rf.fixture_build()
        catalog, sets, strategies = _one_set_catalog(build)
        decision = decide(_inputs(build, catalog, sets, strategies, scenario=GI_SCENARIO))
        intent = decision.authoring_request_intent
        assert intent is not None
        assert intent.scenario_hash == "fixture-scenario-hash"
        assert intent.reasons == (RecommendationAbstentionReason.NO_APPROVED_MATCH,)
        assert decision.matches == ()


class TestPurity:
    def test_the_runtime_module_imports_no_model_index_or_transport(self) -> None:
        # The enforced boundary is the import-linter contract; this reads the
        # source so a local edit fails here first, with a clearer message.
        from importlib.util import find_spec
        from pathlib import Path

        spec = find_spec("rag.runtime.decide")
        assert spec is not None and spec.origin is not None
        text = Path(spec.origin).read_text(encoding="utf-8")
        for forbidden in ("import httpx", "import requests", "rag.authoring", "sklearn"):
            assert forbidden not in text
