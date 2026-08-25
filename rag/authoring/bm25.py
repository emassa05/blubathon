"""Okapi BM25 over document chunks (SPEC 9.4, C25).

Lexical retrieval is the part of the pipeline that always works: it needs no
model, no licence and no network, which is why `lexical_only` is a complete mode
rather than a degraded one.

Everything that could change a ranking is explicit and hashed into the build
manifest: the tokenizer, `k1`, `b`, and the tie-break. Ties are resolved by
`chunk_sha256`, so two builds of the same corpus produce the same order on the
same machine and on another one.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from packages.shared.domain.rag import DocumentChunk

TOKENIZER_VERSION: Final = "tokenizer-unicode-word-0.3.0"
BM25_VERSION: Final = "bm25-okapi-0.3.0"

# Okapi defaults. They are library parameters, not clinical decisions, so they
# live in the build manifest rather than in the SPEC 15 registry.
BM25_K1: Final = 1.2
BM25_B: Final = 0.75

_TOKEN: Final = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> tuple[str, ...]:
    """NFC, casefold, Unicode word runs. No stemming and no stop list.

    Both are language-dependent choices that would have to be versioned,
    reviewed and justified per corpus language; v0.3 does not make them.
    """

    normalized = unicodedata.normalize("NFC", text).casefold()
    return tuple(_TOKEN.findall(normalized))


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    """One retrieved chunk with its score and its 1-based rank."""

    document_chunk_id: UUID
    chunk_sha256: str
    score: float
    rank: int


class Bm25Index:
    """An in-memory lexical index over the chunks of one corpus version."""

    def __init__(
        self,
        chunks: Iterable[DocumentChunk],
        *,
        k1: float = BM25_K1,
        b: float = BM25_B,
    ) -> None:
        self._k1 = float(k1)
        self._b = float(b)
        self._chunks: tuple[DocumentChunk, ...] = tuple(chunks)
        self._frequencies: list[Mapping[str, int]] = []
        self._lengths: list[int] = []
        document_frequency: Counter[str] = Counter()
        for chunk in self._chunks:
            tokens = tokenize(chunk.text)
            counts = Counter(tokens)
            self._frequencies.append(counts)
            self._lengths.append(len(tokens))
            document_frequency.update(counts.keys())
        self._document_frequency = document_frequency
        self._average_length = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0

    @property
    def size(self) -> int:
        return len(self._chunks)

    @property
    def parameters(self) -> dict[str, float]:
        """What the manifest records so this ranking can be reproduced."""

        return {"k1": self._k1, "b": self._b}

    def _idf(self, term: str) -> float:
        # Robertson/Sparck Jones with the +0.5 smoothing, floored at zero so a
        # term present in every chunk cannot push a score negative.
        total = len(self._chunks)
        seen = self._document_frequency.get(term, 0)
        return max(0.0, math.log(1.0 + (total - seen + 0.5) / (seen + 0.5)))

    def score(self, query_tokens: Iterable[str], index: int) -> float:
        counts = self._frequencies[index]
        length = self._lengths[index]
        if self._average_length == 0.0:
            return 0.0
        norm = self._k1 * (1.0 - self._b + self._b * length / self._average_length)
        total = 0.0
        for term in query_tokens:
            frequency = counts.get(term, 0)
            if frequency == 0:
                continue
            total += self._idf(term) * frequency * (self._k1 + 1.0) / (frequency + norm)
        return total

    def search(self, query: str, *, top_k: int) -> tuple[ScoredChunk, ...]:
        """Top `k` chunks by BM25, ties broken by `chunk_sha256` (SPEC 9.4)."""

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        tokens = tokenize(query)
        scored: list[tuple[float, DocumentChunk]] = []
        for index, chunk in enumerate(self._chunks):
            score = self.score(tokens, index)
            if score > 0.0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_sha256))
        return tuple(
            ScoredChunk(
                document_chunk_id=chunk.document_chunk_id,
                chunk_sha256=chunk.chunk_sha256,
                score=score,
                rank=position + 1,
            )
            for position, (score, chunk) in enumerate(scored[:top_k])
        )
