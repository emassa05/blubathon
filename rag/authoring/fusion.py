"""Reciprocal Rank Fusion for the hybrid pipeline (SPEC 9.4, C27).

RRF combines rankings without pretending their scores share a scale: a BM25
score and a cosine similarity are not comparable numbers, but their ranks are
comparable positions. Each retriever contributes `1 / (60 + rank)` with ranks
starting at 1, and the final tie-break is `chunk_sha256`.

Nothing here runs in `lexical_only`. In that mode BM25 returns the final chunks
directly and the manifest says so, rather than simulating a hybrid pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

from packages.shared.constants import RAG_RRF_K
from rag.authoring.bm25 import ScoredChunk


@dataclass(frozen=True, slots=True)
class FusedChunk:
    """One chunk after fusion, with the ranks each retriever gave it."""

    document_chunk_id: UUID
    chunk_sha256: str
    rrf_score: float
    rank: int
    retriever_ranks: tuple[int | None, ...]


def reciprocal_rank_fusion(
    rankings: Sequence[Iterable[ScoredChunk]],
    *,
    k: int = RAG_RRF_K,
    top_k: int,
) -> tuple[FusedChunk, ...]:
    """Fuse ranked lists into one order, deterministic down to the tie-break."""

    if k <= 0:
        raise ValueError("the RRF constant must be positive")
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    materialised = [tuple(ranking) for ranking in rankings]
    hashes: dict[UUID, str] = {}
    ranks: dict[UUID, list[int | None]] = {}
    for position, ranking in enumerate(materialised):
        for scored in ranking:
            hashes.setdefault(scored.document_chunk_id, scored.chunk_sha256)
            row = ranks.setdefault(scored.document_chunk_id, [None] * len(materialised))
            if row[position] is None or scored.rank < row[position]:
                row[position] = scored.rank

    scored_ids = [
        (
            sum(1.0 / (k + rank) for rank in row if rank is not None),
            hashes[chunk_id],
            chunk_id,
            tuple(row),
        )
        for chunk_id, row in ranks.items()
    ]
    scored_ids.sort(key=lambda item: (-item[0], item[1]))
    return tuple(
        FusedChunk(
            document_chunk_id=chunk_id,
            chunk_sha256=chunk_hash,
            rrf_score=score,
            rank=position + 1,
            retriever_ranks=row,
        )
        for position, (score, chunk_hash, chunk_id, row) in enumerate(scored_ids[:top_k])
    )
