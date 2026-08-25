"""The document, chunk, citation, review and activation domain (SPEC 9.2-9.6)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from packages.shared.enums import (
    AccreditationCapability,
    AuthoringReviewDecision,
    AuthoringReviewKind,
    AuthoringReviewObjectType,
    CatalogStatus,
    DocumentStatus,
    FieldCode,
    StrategyStatus,
)
from rag.domain.activation import (
    catalog_activation_decision,
    set_activation_decision,
    set_content_sha256,
    strategy_activation_decision,
    strategy_content_sha256,
    suspended_by_dependency,
)
from rag.domain.chunking import ChunkPlan, chunk_document, split_paragraphs
from rag.domain.citations import verify_citation, verify_strategy_citations
from rag.domain.documents import (
    RightsNotDeclaredError,
    build_corpus_version,
    build_document_version,
    is_indexable,
)
from rag.domain.normalization import normalize_document_text
from rag.domain.reviews import ReviewLedger, required_capability
from rag.domain.text_guard import (
    FreeTextLeakError,
    assert_literature_only,
    assert_no_clinical_text,
    literature,
)
from tests.p1 import rag_factories as rf
from tests.p1.factories import ident

EVIDENCE = frozenset({AccreditationCapability.EVIDENCE_REVIEW})
CLINICAL = frozenset({AccreditationCapability.STRATEGY_REVIEW})
ACTIVATION = frozenset({AccreditationCapability.CATALOG_ACTIVATION})


def _ledger(*, reviews, actors):
    return ReviewLedger(reviews, actors, cutoff=rf.NOW)


def _reviewed_strategy(
    build, *, label="sleep", quote=None, action=None, claim=None, predicate=None
):
    """A strategy plus the two distinct approved reviews that activate it."""

    from packages.shared.domain.rag import ScenarioPredicate

    draft = rf.strategy(
        label,
        build=build,
        quote=quote or rf.SLEEP_QUOTE,
        action_text=action or rf.ACTION_TEXT_SLEEP,
        claim_text=claim or rf.CLAIM_TEXT_SLEEP,
        predicate=predicate or ScenarioPredicate(),
        status=StrategyStatus.CLINICAL_REVIEWED,
    )
    sealed = strategy_content_sha256(draft)
    evidence = rf.review(
        f"{label}-evidence",
        actor_label="evidence-reviewer",
        object_type=AuthoringReviewObjectType.STRATEGY,
        object_version_id=draft.strategy_version_id,
        review_kind=AuthoringReviewKind.EVIDENCE,
        content_sha256=sealed,
    )
    clinical = rf.review(
        f"{label}-clinical",
        actor_label="clinical-reviewer",
        object_type=AuthoringReviewObjectType.STRATEGY,
        object_version_id=draft.strategy_version_id,
        review_kind=AuthoringReviewKind.CLINICAL,
        content_sha256=sealed,
    )
    active = rf.strategy(
        label,
        build=build,
        quote=quote or rf.SLEEP_QUOTE,
        action_text=action or rf.ACTION_TEXT_SLEEP,
        claim_text=claim or rf.CLAIM_TEXT_SLEEP,
        predicate=predicate or ScenarioPredicate(),
        status=StrategyStatus.ACTIVE,
        evidence_review_id=evidence.authoring_review_id,
        clinical_review_id=clinical.authoring_review_id,
    )
    actors = (
        rf.accreditation("evidence-reviewer", capabilities=EVIDENCE),
        rf.accreditation("clinical-reviewer", capabilities=CLINICAL),
    )
    return active, (evidence, clinical), actors


class TestNormalization:
    def test_crlf_and_decomposed_forms_normalise_to_one_representation(self) -> None:
        composed = normalize_document_text("niño\r\nsueno")
        assert composed == "niño\nsueno"

    def test_normalisation_does_not_collapse_whitespace(self) -> None:
        # A citation that needs help to match is not literal (SPEC 9.5).
        assert normalize_document_text("dos  espacios") == "dos  espacios"


class TestChunking:
    def test_every_chunk_is_a_verbatim_span_of_the_document(self) -> None:
        build = rf.fixture_build()
        for chunk in build.chunks:
            source_text = (
                rf.SLEEP_TEXT
                if chunk.document_version_id == build.documents[0].document_version_id
                else rf.GI_TEXT
            )
            assert chunk.text in normalize_document_text(source_text)

    def test_locator_names_the_paragraphs_a_reviewer_can_open(self) -> None:
        paragraphs = split_paragraphs(rf.SLEEP_TEXT)
        assert [paragraph.index for paragraph in paragraphs] == [1, 2, 3, 4]
        build = rf.fixture_build()
        assert {chunk.locator for chunk in build.chunks} == {
            "paragraphs 1-2",
            "paragraphs 3-4",
            "paragraphs 1-3",
        }

    def test_chunking_is_deterministic_across_builds(self) -> None:
        first = rf.fixture_build()
        second = rf.fixture_build()
        assert [chunk.chunk_sha256 for chunk in first.chunks] == [
            chunk.chunk_sha256 for chunk in second.chunks
        ]

    def test_a_paragraph_longer_than_the_budget_is_never_split(self) -> None:
        chunks = chunk_document(
            document_version_id=ident("doc:long"),
            text="uno dos tres cuatro cinco seis siete ocho nueve diez",
            plan=ChunkPlan(chunk_size=3, chunk_overlap=1),
            chunk_id_for=lambda locator: ident(f"chunk:{locator}"),
        )
        assert len(chunks) == 1
        assert chunks[0].locator == "paragraph 1"

    def test_overlap_must_be_smaller_than_the_chunk(self) -> None:
        with pytest.raises(ValueError, match="overlap"):
            ChunkPlan(chunk_size=10, chunk_overlap=10)


class TestDocumentRights:
    def test_an_undeclared_rights_basis_refuses_to_become_a_version(self) -> None:
        with pytest.raises(RightsNotDeclaredError):
            build_document_version(
                rf.source("blocked", rf.SLEEP_TEXT, rights_basis="undeclared"),
                document_version_id=ident("doc:blocked"),
                extraction_manifest_id=ident("extraction:blocked"),
            )

    def test_a_withdrawn_version_is_not_indexable_and_cannot_join_a_corpus(self) -> None:
        build = rf.fixture_build()
        withdrawn = build.documents[0].model_copy(update={"status": DocumentStatus.WITHDRAWN})
        assert not is_indexable(withdrawn)
        with pytest.raises(ValueError, match="withdrawn"):
            build_corpus_version(
                (withdrawn,),
                corpus_version="corpus-withdrawn",
                authoring_build_manifest_id=ident("manifest:withdrawn"),
                created_at=rf.BUILT_AT,
            )

    def test_the_text_hash_covers_the_normalised_text_not_the_raw_bytes(self) -> None:
        crlf = rf.source("crlf", rf.SLEEP_TEXT.replace("\n", "\r\n"))
        lf = rf.source("crlf", rf.SLEEP_TEXT)
        built = [
            build_document_version(
                document,
                document_version_id=ident("doc:crlf"),
                extraction_manifest_id=ident("extraction:crlf"),
            )
            for document in (crlf, lf)
        ]
        assert built[0].extracted_text_sha256 == built[1].extracted_text_sha256
        assert built[0].original_bytes_sha256 != built[1].original_bytes_sha256


class TestCitations:
    def test_a_literal_quote_verifies(self) -> None:
        build = rf.fixture_build()
        strategy, _, _ = _reviewed_strategy(build)
        results = verify_strategy_citations(strategy, build.chunks)
        assert all(result.verified for result in results)

    def test_a_quote_that_is_not_in_the_chunk_fails(self) -> None:
        build = rf.fixture_build()
        strategy, _, _ = _reviewed_strategy(build)
        fabricated = strategy.citations[0].model_copy(
            update={"quoted_text": "una frase que nadie escribio"}
        )
        result = verify_citation(
            fabricated, {chunk.document_chunk_id: chunk for chunk in build.chunks}
        )
        assert result.failure == "quote_not_literal"

    def test_a_chunk_whose_hash_changed_fails(self) -> None:
        build = rf.fixture_build()
        strategy, _, _ = _reviewed_strategy(build)
        chunks = {chunk.document_chunk_id: chunk for chunk in build.chunks}
        target = chunks[strategy.citations[0].document_chunk_id]
        chunks[target.document_chunk_id] = target.model_copy(update={"chunk_sha256": "b" * 64})
        assert verify_citation(strategy.citations[0], chunks).failure == "chunk_hash_mismatch"


class TestReviewLedger:
    def test_capability_is_never_substituted_between_review_kinds(self) -> None:
        assert (
            required_capability(AuthoringReviewObjectType.STRATEGY, AuthoringReviewKind.EVIDENCE)
            is AccreditationCapability.EVIDENCE_REVIEW
        )
        assert (
            required_capability(AuthoringReviewObjectType.STRATEGY, AuthoringReviewKind.CLINICAL)
            is AccreditationCapability.STRATEGY_REVIEW
        )

    def test_a_review_without_the_capability_is_not_a_review(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, _ = _reviewed_strategy(build)
        unaccredited = (
            rf.accreditation("evidence-reviewer", capabilities=frozenset()),
            rf.accreditation("clinical-reviewer", capabilities=CLINICAL),
        )
        ledger = _ledger(reviews=reviews, actors=unaccredited)
        assert (
            ledger.approved_review(
                review_id=reviews[0].authoring_review_id,
                object_type=AuthoringReviewObjectType.STRATEGY,
                object_version_id=strategy.strategy_version_id,
                review_kind=AuthoringReviewKind.EVIDENCE,
                content_sha256=strategy_content_sha256(strategy),
            )
            is None
        )

    def test_a_review_of_another_hash_does_not_apply(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        ledger = _ledger(reviews=reviews, actors=actors)
        assert (
            ledger.approved_review(
                review_id=reviews[0].authoring_review_id,
                object_type=AuthoringReviewObjectType.STRATEGY,
                object_version_id=strategy.strategy_version_id,
                review_kind=AuthoringReviewKind.EVIDENCE,
                content_sha256="c" * 64,
            )
            is None
        )

    def test_changes_requested_supersedes_an_earlier_approval(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        sealed = strategy_content_sha256(strategy)
        correction = rf.review(
            "sleep-evidence-correction",
            actor_label="evidence-reviewer",
            object_type=AuthoringReviewObjectType.STRATEGY,
            object_version_id=strategy.strategy_version_id,
            review_kind=AuthoringReviewKind.EVIDENCE,
            content_sha256=sealed,
            decision=AuthoringReviewDecision.CHANGES_REQUESTED,
            reviewed_at=datetime(2026, 8, 21, tzinfo=UTC),
        ).model_copy(update={"supersedes_id": reviews[0].authoring_review_id})
        ledger = _ledger(reviews=(*reviews, correction), actors=actors)
        assert (
            ledger.approved_review(
                review_id=reviews[0].authoring_review_id,
                object_type=AuthoringReviewObjectType.STRATEGY,
                object_version_id=strategy.strategy_version_id,
                review_kind=AuthoringReviewKind.EVIDENCE,
                content_sha256=sealed,
            )
            is None
        )


class TestActivation:
    def test_a_fully_reviewed_strategy_activates(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        decision = strategy_activation_decision(
            strategy,
            chunks=build.chunks,
            documents=build.documents,
            ledger=_ledger(reviews=reviews, actors=actors),
        )
        assert decision.approved, decision.blockers

    def test_one_person_cannot_perform_both_reviews(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, _ = _reviewed_strategy(build)
        same_person = (
            rf.accreditation("evidence-reviewer", capabilities=EVIDENCE | CLINICAL).model_copy(
                update={"actor_id": ident("actor:evidence-reviewer")}
            ),
        )
        clinical_by_same_actor = reviews[1].model_copy(
            update={
                "actor_id": ident("actor:evidence-reviewer"),
                "accreditation_id": ident("accreditation:evidence-reviewer"),
            }
        )
        decision = strategy_activation_decision(
            strategy,
            chunks=build.chunks,
            documents=build.documents,
            ledger=_ledger(reviews=(reviews[0], clinical_by_same_actor), actors=same_person),
        )
        assert "reviewers_not_distinct" in decision.blockers

    def test_without_a_clinical_reviewer_activation_is_blocked_by_that_reason(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        no_clinical = strategy.model_copy(update={"clinical_review_id": None})
        decision = strategy_activation_decision(
            no_clinical,
            chunks=build.chunks,
            documents=build.documents,
            ledger=_ledger(reviews=(reviews[0],), actors=actors),
        )
        assert decision.blockers == ("clinical_review_unavailable",)

    def test_a_fabricated_citation_blocks_activation(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        fabricated = strategy.model_copy(
            update={
                "citations": (
                    strategy.citations[0].model_copy(update={"quoted_text": "cita inventada"}),
                )
            }
        )
        decision = strategy_activation_decision(
            fabricated,
            chunks=build.chunks,
            documents=build.documents,
            ledger=_ledger(reviews=reviews, actors=actors),
        )
        assert "citation_not_verified" in decision.blockers

    def test_a_retired_source_suspends_its_dependants(self) -> None:
        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        withdrawn = tuple(
            document.model_copy(update={"status": DocumentStatus.WITHDRAWN})
            for document in build.documents
        )
        assert suspended_by_dependency(
            strategy,
            chunks={chunk.document_chunk_id: chunk for chunk in build.chunks},
            documents={document.document_version_id: document for document in withdrawn},
        )
        decision = strategy_activation_decision(
            strategy,
            chunks=build.chunks,
            documents=withdrawn,
            ledger=_ledger(reviews=reviews, actors=actors),
        )
        assert "source_retired" in decision.blockers

    def test_a_set_activates_only_when_its_predicate_implies_each_strategy(self) -> None:
        from packages.shared.domain.rag import ScenarioPredicate

        build = rf.fixture_build()
        narrow = ScenarioPredicate(required_field_values={FieldCode.ALERTNESS: ("high",)})
        strategy, reviews, actors = _reviewed_strategy(build, predicate=narrow)
        loose = rf.recommendation_set(
            "loose",
            strategy_version_ids=(strategy.strategy_version_id,),
            predicate=ScenarioPredicate(),
            status=CatalogStatus.REVIEWED,
            clinical_review_id=ident("review:set-clinical"),
        )
        set_review = rf.review(
            "set-clinical",
            actor_label="clinical-reviewer",
            object_type=AuthoringReviewObjectType.RECOMMENDATION_SET,
            object_version_id=loose.recommendation_set_id,
            review_kind=AuthoringReviewKind.CLINICAL,
            content_sha256=set_content_sha256(loose),
        )
        decision = set_activation_decision(
            loose,
            strategies={strategy.strategy_version_id: strategy},
            ledger=_ledger(reviews=(*reviews, set_review), actors=actors),
        )
        assert "predicate_not_implied" in decision.blockers

    def test_a_catalogue_needs_its_own_activation_review(self) -> None:
        from packages.shared.domain.rag import ScenarioPredicate

        build = rf.fixture_build()
        strategy, reviews, actors = _reviewed_strategy(build)
        version = rf.recommendation_set(
            "primary",
            strategy_version_ids=(strategy.strategy_version_id,),
            predicate=ScenarioPredicate(),
            status=CatalogStatus.ACTIVE,
            clinical_review_id=ident("review:set-clinical"),
        )
        catalog = rf.catalog(
            "demo",
            build=build,
            set_ids=(version.recommendation_set_id,),
            status=CatalogStatus.DRAFT,
        )
        decision = catalog_activation_decision(
            catalog,
            sets={version.recommendation_set_id: version},
            ledger=_ledger(reviews=reviews, actors=actors),
        )
        assert "catalog_activation_review_missing" in decision.blockers

        activation = rf.review(
            "catalog-activation",
            actor_label="tenant-admin",
            object_type=AuthoringReviewObjectType.CATALOG,
            object_version_id=catalog.tenant_id,
            review_kind=AuthoringReviewKind.CATALOG_ACTIVATION,
            content_sha256=catalog.content_sha256,
        )
        approved = rf.catalog(
            "demo",
            build=build,
            set_ids=(version.recommendation_set_id,),
            status=CatalogStatus.ACTIVE,
            activation_review_id=activation.authoring_review_id,
        )
        decision = catalog_activation_decision(
            approved,
            sets={version.recommendation_set_id: version},
            ledger=_ledger(
                reviews=(*reviews, activation),
                actors=(*actors, rf.accreditation("tenant-admin", capabilities=ACTIVATION)),
            ),
        )
        assert decision.approved, decision.blockers


class TestFreeTextGuard:
    def test_only_authorised_literature_may_be_chunked_or_prompted(self) -> None:
        build = rf.fixture_build()
        authorised = build.authorised_document_version_ids
        assert assert_literature_only(
            (literature("un fragmento", next(iter(authorised))),), authorised=authorised
        )
        with pytest.raises(FreeTextLeakError):
            assert_literature_only(
                (rf_note(),),
                authorised=authorised,
            )

    def test_an_identifier_in_a_payload_stops_the_build(self) -> None:
        with pytest.raises(FreeTextLeakError):
            assert_no_clinical_text(
                "consulta generalizada sobre 11111111-2222-4333-8444-555555555555",
                sentinels=("11111111-2222-4333-8444-555555555555",),
            )


def rf_note():
    from rag.domain.text_guard import TextProvenance

    return TextProvenance(text="el nino durmio mal", kind="clinical_free_text")
