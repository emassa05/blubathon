"""Document, chunk, citation and text-safety domain tests."""

from __future__ import annotations

import importlib.util

import pytest

from packages.shared.domain.rag import StrategyCitation
from packages.shared.enums import DocumentStatus
from rag.domain.chunking import ChunkPlan, chunk_document, split_paragraphs
from rag.domain.citations import verify_citation
from rag.domain.documents import (
    RightsNotDeclaredError,
    build_corpus_version,
    build_document_version,
    is_indexable,
)
from rag.domain.normalization import normalize_document_text
from rag.domain.text_guard import (
    FreeTextLeakError,
    assert_literature_only,
    assert_no_clinical_text,
    literature,
)
from tests.p1 import rag_factories as rf
from tests.p1.factories import ident


def test_curated_runtime_package_no_longer_exists() -> None:
    assert importlib.util.find_spec("rag.runtime") is None


def _citation(build, quote: str = rf.SLEEP_QUOTE) -> StrategyCitation:
    chunk = rf.chunk_containing(build, quote)
    return StrategyCitation(
        citation_id=ident("citation:literal"),
        claim_id=ident("claim:literal"),
        document_chunk_id=chunk.document_chunk_id,
        locator=chunk.locator,
        quoted_text=quote,
        chunk_sha256=chunk.chunk_sha256,
        canonical_url="https://example.invalid/fixtures/quoted",
    )


class TestNormalization:
    def test_crlf_and_decomposed_forms_normalise_to_one_representation(self) -> None:
        composed = normalize_document_text("niño\r\nsueno")
        assert composed == "niño\nsueno"

    def test_normalisation_does_not_collapse_whitespace(self) -> None:
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
        citation = _citation(build)
        result = verify_citation(
            citation, {chunk.document_chunk_id: chunk for chunk in build.chunks}
        )
        assert result.verified

    def test_a_quote_that_is_not_in_the_chunk_fails(self) -> None:
        build = rf.fixture_build()
        fabricated = _citation(build).model_copy(
            update={"quoted_text": "una frase que nadie escribio"}
        )
        result = verify_citation(
            fabricated, {chunk.document_chunk_id: chunk for chunk in build.chunks}
        )
        assert result.failure == "quote_not_literal"

    def test_a_chunk_whose_hash_changed_fails(self) -> None:
        build = rf.fixture_build()
        citation = _citation(build)
        chunks = {chunk.document_chunk_id: chunk for chunk in build.chunks}
        target = chunks[citation.document_chunk_id]
        chunks[target.document_chunk_id] = target.model_copy(update={"chunk_sha256": "b" * 64})
        assert verify_citation(citation, chunks).failure == "chunk_hash_mismatch"


class TestFreeTextGuard:
    def test_only_authorised_literature_may_be_chunked_or_prompted(self) -> None:
        build = rf.fixture_build()
        authorised = build.authorised_document_version_ids
        assert assert_literature_only(
            (literature("un fragmento", next(iter(authorised))),), authorised=authorised
        )
        with pytest.raises(FreeTextLeakError):
            assert_literature_only((_clinical_note(),), authorised=authorised)

    def test_an_identifier_in_a_payload_stops_the_build(self) -> None:
        with pytest.raises(FreeTextLeakError):
            assert_no_clinical_text(
                "consulta generalizada sobre 11111111-2222-4333-8444-555555555555",
                sentinels=("11111111-2222-4333-8444-555555555555",),
            )


def _clinical_note():
    from rag.domain.text_guard import TextProvenance

    return TextProvenance(text="el nino durmio mal", kind="clinical_free_text")
