"""Retrieval, fusion, the declared build mode and the optional local draft."""

from __future__ import annotations

import json
import urllib.error

import pytest

from packages.shared.constants import RAG_FINAL_CHUNKS, RAG_RRF_K
from packages.shared.enums import RetrievalMode
from rag.authoring.bm25 import Bm25Index, ScoredChunk, tokenize
from rag.authoring.build import build_authoring_corpus
from rag.authoring.drafting import (
    DraftRequest,
    DraftUnavailableError,
    load_prompt,
    render_fragments,
    request_draft,
)
from rag.authoring.fusion import reciprocal_rank_fusion
from rag.authoring.retrieval import (
    DenseModelNotRegisteredError,
    RetrievalPlan,
    resolve_retrieval_mode,
    retrieve,
)
from rag.authoring.transports import DraftRefusedError
from rag.domain.text_guard import FreeTextLeakError
from tests.p1 import rag_factories as rf
from tests.p1.factories import ident


class SimulatedDense:
    """A stand-in embedding model. Tests never depend on a live daemon."""

    model_id = "fixture-dense"
    model_sha256 = "d" * 64

    def __init__(self, hits: tuple[ScoredChunk, ...]) -> None:
        self._hits = hits

    def search(self, query: str, *, top_k: int) -> tuple[ScoredChunk, ...]:
        return self._hits[:top_k]


class SimulatedTransport:
    """A simulated local LLM transport."""

    model_id = "fixture-llm"
    model_sha256 = "e" * 64

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps(
            {
                "purpose_es": "Borrador de prueba.",
                "action_text_es": rf.ACTION_TEXT_SLEEP,
                "claims": [],
            }
        )


class UnreachableTransport:
    """A daemon that is not listening. `urllib` reports this as `URLError`."""

    model_id = "fixture-unreachable"
    model_sha256 = "f" * 64

    def complete(self, prompt: str) -> str:
        raise urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))


class SilentTransport:
    """A model that answers with nothing. The transport calls that a refusal."""

    model_id = "fixture-silent"
    model_sha256 = "0" * 64

    def complete(self, prompt: str) -> str:
        raise DraftRefusedError("the model returned an empty response")


class TestTokenizer:
    def test_case_and_unicode_form_do_not_change_the_tokens(self) -> None:
        assert tokenize("Rutina  DE sueño") == tokenize("rutina de sueño")

    def test_no_stemming_or_stop_list_is_applied(self) -> None:
        assert tokenize("la rutina") == ("la", "rutina")


class TestBm25:
    def test_a_query_retrieves_the_chunk_that_contains_it(self) -> None:
        build = rf.fixture_build()
        hits = build.index.search("ruido y luz intensa", top_k=RAG_FINAL_CHUNKS)
        assert hits
        top = rf.chunk_containing(build, rf.SLEEP_QUOTE)
        assert hits[0].chunk_sha256 == top.chunk_sha256

    def test_ranking_is_deterministic_and_ties_break_on_the_chunk_hash(self) -> None:
        build = rf.fixture_build()
        first = build.index.search("patron", top_k=RAG_FINAL_CHUNKS)
        second = Bm25Index(build.chunks).search("patron", top_k=RAG_FINAL_CHUNKS)
        assert [hit.chunk_sha256 for hit in first] == [hit.chunk_sha256 for hit in second]
        assert [hit.rank for hit in first] == list(range(1, len(first) + 1))

    def test_a_query_with_no_overlap_returns_nothing_rather_than_noise(self) -> None:
        build = rf.fixture_build()
        assert build.index.search("palabraquenoexiste", top_k=RAG_FINAL_CHUNKS) == ()


class TestFusion:
    def test_rrf_sums_one_over_k_plus_rank_with_ranks_from_one(self) -> None:
        lexical = (ScoredChunk(ident("a"), "a" * 64, 3.0, 1),)
        dense = (ScoredChunk(ident("a"), "a" * 64, 0.9, 2),)
        fused = reciprocal_rank_fusion((lexical, dense), k=RAG_RRF_K, top_k=1)
        assert fused[0].rrf_score == pytest.approx(1 / 61 + 1 / 62)
        assert fused[0].retriever_ranks == (1, 2)

    def test_a_chunk_found_by_one_retriever_still_scores(self) -> None:
        lexical = (ScoredChunk(ident("a"), "a" * 64, 3.0, 1),)
        dense = (ScoredChunk(ident("b"), "b" * 64, 0.9, 1),)
        fused = reciprocal_rank_fusion((lexical, dense), k=RAG_RRF_K, top_k=2)
        assert {item.chunk_sha256 for item in fused} == {"a" * 64, "b" * 64}
        # Equal scores fall back to the chunk hash, so the order is reproducible.
        assert [item.chunk_sha256 for item in fused] == ["a" * 64, "b" * 64]


class TestDeclaredMode:
    def test_without_a_registered_model_the_mode_is_lexical_only(self) -> None:
        assert resolve_retrieval_mode(None) is RetrievalMode.LEXICAL_ONLY

    def test_lexical_only_returns_the_final_chunks_directly(self) -> None:
        build = rf.fixture_build()
        result = retrieve("rutina de sueño", index=build.index, plan=RetrievalPlan.lexical_only())
        assert result.mode is RetrievalMode.LEXICAL_ONLY
        assert result.dense == ()
        assert result.fused == ()

    def test_a_hybrid_plan_without_a_model_refuses_instead_of_falling_back(self) -> None:
        build = rf.fixture_build()
        with pytest.raises(DenseModelNotRegisteredError):
            retrieve("rutina", index=build.index, plan=RetrievalPlan(mode=RetrievalMode.HYBRID))

    def test_a_lexical_only_plan_carries_no_dense_parameters(self) -> None:
        with pytest.raises(ValueError, match="lexical_only"):
            RetrievalPlan(mode=RetrievalMode.LEXICAL_ONLY, dense_top_k=20, rrf_k=60)

    def test_hybrid_fuses_both_rankings_when_a_model_is_registered(self) -> None:
        build = rf.fixture_build()
        dense_hit = ScoredChunk(
            build.chunks[-1].document_chunk_id, build.chunks[-1].chunk_sha256, 0.8, 1
        )
        result = retrieve(
            "rutina",
            index=build.index,
            plan=RetrievalPlan(mode=RetrievalMode.HYBRID),
            dense=SimulatedDense((dense_hit,)),
        )
        assert result.mode is RetrievalMode.HYBRID
        assert result.fused


class TestBuildManifest:
    def test_the_manifest_declares_lexical_only_and_no_dense_parameters(self) -> None:
        build = rf.fixture_build()
        manifest = build.manifest
        assert manifest.retrieval_mode is RetrievalMode.LEXICAL_ONLY
        assert manifest.dense_model_id is None
        assert manifest.dense_top_k is None
        assert manifest.rrf_k is None

    def test_the_manifest_hash_changes_with_the_chunk_plan(self) -> None:
        from rag.domain.chunking import ChunkPlan

        first = rf.fixture_build()
        second = rf.fixture_build(chunk_plan=ChunkPlan(chunk_size=80, chunk_overlap=10))
        assert first.manifest.content_sha256 != second.manifest.content_sha256

    def test_two_builds_of_the_same_corpus_hash_the_same(self) -> None:
        assert rf.fixture_build().manifest.content_sha256 == (
            rf.fixture_build().manifest.content_sha256
        )

    def test_an_undeclared_document_stops_the_build(self) -> None:
        from rag.domain.documents import RightsNotDeclaredError

        with pytest.raises(RightsNotDeclaredError):
            build_authoring_corpus(
                (rf.source("blocked", rf.SLEEP_TEXT, rights_basis="undeclared"),),
                corpus_version="corpus-blocked",
                id_for=ident,
                built_at=rf.BUILT_AT,
            )


class TestDrafting:
    def test_the_prompt_is_versioned_package_data_with_declared_schemas(self) -> None:
        prompt = load_prompt()
        assert prompt.prompt_version == "authoring-draft-0.5.0"
        assert prompt.input_schema["required"] == ["generalized_question_es", "fragments"]
        assert "purpose_es" in prompt.output_schema["properties"]
        assert len(prompt.prompt_sha256) == 64

    def test_without_a_registered_model_there_is_no_draft(self) -> None:
        build = rf.fixture_build()
        with pytest.raises(DraftUnavailableError):
            request_draft(
                DraftRequest("consulta generalizada", build.chunks),
                transport=None,
                authorised_document_version_ids=build.authorised_document_version_ids,
            )

    def test_a_draft_only_ever_sees_authorised_literature(self) -> None:
        build = rf.fixture_build()
        other = rf.fixture_build(sources=(rf.source("gi", rf.GI_TEXT),))
        with pytest.raises(FreeTextLeakError):
            request_draft(
                DraftRequest("consulta generalizada", build.chunks),
                transport=SimulatedTransport(),
                authorised_document_version_ids=other.authorised_document_version_ids,
            )

    def test_a_clinical_sentinel_in_the_prompt_stops_the_draft(self) -> None:
        build = rf.fixture_build()
        with pytest.raises(FreeTextLeakError):
            request_draft(
                DraftRequest("consulta sobre rutina", build.chunks),
                transport=SimulatedTransport(),
                authorised_document_version_ids=build.authorised_document_version_ids,
                clinical_sentinels=("rutina",),
            )

    def test_the_draft_records_prompt_and_model_provenance(self) -> None:
        build = rf.fixture_build()
        transport = SimulatedTransport()
        result = request_draft(
            DraftRequest("consulta generalizada", build.chunks),
            transport=transport,
            authorised_document_version_ids=build.authorised_document_version_ids,
        )
        assert result.model_id == "fixture-llm"
        assert result.prompt_version == load_prompt().prompt_version
        assert result.payload()["purpose_es"] == "Borrador de prueba."
        # The draft is a draft: it carries no review and activates nothing.
        assert result.payload()["claims"] == []

    def test_a_model_that_cannot_be_reached_is_a_draft_that_is_unavailable(self) -> None:
        """A dead daemon has to arrive as `DraftUnavailableError`, not `URLError`.

        The caller abstains on `DraftUnavailableError`. A raw `URLError` walked
        past that branch, killed the background task that generates the
        recommendation, and left the row in `pending` with nobody working on it.
        """

        build = rf.fixture_build()
        with pytest.raises(DraftUnavailableError) as failure:
            request_draft(
                DraftRequest("consulta generalizada", build.chunks),
                transport=UnreachableTransport(),
                authorised_document_version_ids=build.authorised_document_version_ids,
            )
        # The original failure is chained, not swallowed: it is still diagnosable.
        assert isinstance(failure.value.__cause__, urllib.error.URLError)

    def test_a_model_that_declines_is_a_draft_that_is_unavailable(self) -> None:
        build = rf.fixture_build()
        with pytest.raises(DraftUnavailableError):
            request_draft(
                DraftRequest("consulta generalizada", build.chunks),
                transport=SilentTransport(),
                authorised_document_version_ids=build.authorised_document_version_ids,
            )

    def test_an_unauthorised_fragment_still_raises_and_is_not_an_abstention(self) -> None:
        """The privacy guard runs before the model call and is never translated.

        Literature that nobody authorised reaching the prompt is a defect. If it
        arrived as `DraftUnavailableError` the caller would file it as an
        ordinary abstention and the leak would never be noticed.
        """

        build = rf.fixture_build()
        other = rf.fixture_build(sources=(rf.source("gi", rf.GI_TEXT),))
        with pytest.raises(FreeTextLeakError):
            request_draft(
                DraftRequest("consulta generalizada", build.chunks),
                transport=UnreachableTransport(),
                authorised_document_version_ids=other.authorised_document_version_ids,
            )

    def test_fragments_are_rendered_in_a_stable_order(self) -> None:
        build = rf.fixture_build()
        assert render_fragments(build.chunks) == render_fragments(reversed(build.chunks))
