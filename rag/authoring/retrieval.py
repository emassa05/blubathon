"""Retrieval in the mode the build actually declares (SPEC 9.4).

Two modes exist and both are complete. `hybrid` needs a dense retriever whose
model has a registered licence, model card and artifact hash; without one the
build resolves to `lexical_only`, says so in the manifest and in the review, and
BM25 returns the final chunks directly.

The refusal in `retrieve` is the point of this module: a hybrid plan without a
dense retriever raises instead of quietly falling back, because a manifest that
claims hybrid and ran lexical is a false reproducibility record. No model is
ever downloaded to make a build succeed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from packages.shared.constants import (
    RAG_DENSE_TOP_K,
    RAG_FINAL_CHUNKS,
    RAG_LEXICAL_TOP_K,
    RAG_RRF_K,
)
from packages.shared.enums import RetrievalMode
from rag.authoring.bm25 import Bm25Index, ScoredChunk
from rag.authoring.fusion import FusedChunk, reciprocal_rank_fusion


@runtime_checkable
class DenseRetriever(Protocol):
    """A registered embedding model. It never receives personal data."""

    @property
    def model_id(self) -> str: ...

    @property
    def model_sha256(self) -> str: ...

    def search(self, query: str, *, top_k: int) -> tuple[ScoredChunk, ...]: ...


class DenseModelNotRegisteredError(RuntimeError):
    """A hybrid build was requested without an approved embedding model."""


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    """The declared mode and its top-k parameters, exactly as hashed."""

    mode: RetrievalMode
    lexical_top_k: int = RAG_LEXICAL_TOP_K
    dense_top_k: int | None = RAG_DENSE_TOP_K
    rrf_k: int | None = RAG_RRF_K
    final_chunk_count: int = RAG_FINAL_CHUNKS

    def __post_init__(self) -> None:
        if self.mode is RetrievalMode.LEXICAL_ONLY and any(
            value is not None for value in (self.dense_top_k, self.rrf_k)
        ):
            raise ValueError("a lexical_only plan carries no dense or RRF parameters")
        if self.mode is RetrievalMode.HYBRID and any(
            value is None for value in (self.dense_top_k, self.rrf_k)
        ):
            raise ValueError("a hybrid plan names its dense top k and RRF k")

    @classmethod
    def lexical_only(cls, *, final_chunk_count: int = RAG_FINAL_CHUNKS) -> RetrievalPlan:
        return cls(
            mode=RetrievalMode.LEXICAL_ONLY,
            dense_top_k=None,
            rrf_k=None,
            final_chunk_count=final_chunk_count,
        )


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """The final fragments and enough detail to explain how they were chosen."""

    mode: RetrievalMode
    chunk_ids: tuple[str, ...]
    lexical: tuple[ScoredChunk, ...]
    dense: tuple[ScoredChunk, ...] = ()
    fused: tuple[FusedChunk, ...] = ()


def resolve_retrieval_mode(dense: DenseRetriever | None) -> RetrievalMode:
    """Hybrid only when a registered dense retriever is actually present."""

    return RetrievalMode.HYBRID if dense is not None else RetrievalMode.LEXICAL_ONLY


def retrieve(
    query: str,
    *,
    index: Bm25Index,
    plan: RetrievalPlan,
    dense: DenseRetriever | None = None,
) -> RetrievalResult:
    """Run the declared pipeline. A hybrid plan without a model refuses."""

    if plan.mode is RetrievalMode.LEXICAL_ONLY:
        lexical = index.search(query, top_k=plan.final_chunk_count)
        return RetrievalResult(
            mode=plan.mode,
            chunk_ids=tuple(str(item.document_chunk_id) for item in lexical),
            lexical=lexical,
        )

    if dense is None:
        raise DenseModelNotRegisteredError(
            "a hybrid build needs a registered embedding model; no model is downloaded "
            "implicitly and retrieval is never simulated (SPEC 9.4)"
        )

    lexical = index.search(query, top_k=plan.lexical_top_k)
    dense_hits = dense.search(query, top_k=plan.dense_top_k or RAG_DENSE_TOP_K)
    fused = reciprocal_rank_fusion(
        (lexical, dense_hits),
        k=plan.rrf_k or RAG_RRF_K,
        top_k=plan.final_chunk_count,
    )
    return RetrievalResult(
        mode=plan.mode,
        chunk_ids=tuple(str(item.document_chunk_id) for item in fused),
        lexical=lexical,
        dense=dense_hits,
        fused=fused,
    )


def ranked_chunk_hashes(items: Iterable[ScoredChunk | FusedChunk]) -> tuple[str, ...]:
    """Chunk hashes in rank order, the shape a manifest records."""

    return tuple(item.chunk_sha256 for item in items)
