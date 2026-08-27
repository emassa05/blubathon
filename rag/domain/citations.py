"""Literal citation verification (INV-24).

The automatic check answers one narrow question: does `quoted_text` appear,
character for character, inside the normalised text of the exact hashed chunk
the citation names, at the locator it names. Whether that fragment supports the
claim is a judgement the `evidence_reviewer` makes; no code decides it.

A mismatch blocks activation. It is never repaired by loosening the comparison.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from packages.shared.domain.rag import DocumentChunk, StrategyCitation, StrategyVersion
from rag.domain.normalization import normalize_document_text, normalize_quote

VerificationFailure = Literal[
    "chunk_unknown",
    "chunk_hash_mismatch",
    "locator_mismatch",
    "quote_not_literal",
]


@dataclass(frozen=True, slots=True)
class CitationVerification:
    """One citation, verified or refused with a stable machine reason."""

    citation_id: UUID
    claim_id: UUID
    verified: bool
    failure: VerificationFailure | None = None


def verify_citation(
    citation: StrategyCitation, chunks: Mapping[UUID, DocumentChunk]
) -> CitationVerification:
    """Check one citation against the chunk it names."""

    chunk = chunks.get(citation.document_chunk_id)
    if chunk is None:
        return CitationVerification(citation.citation_id, citation.claim_id, False, "chunk_unknown")
    if chunk.chunk_sha256 != citation.chunk_sha256:
        return CitationVerification(
            citation.citation_id, citation.claim_id, False, "chunk_hash_mismatch"
        )
    if chunk.locator != citation.locator:
        return CitationVerification(
            citation.citation_id, citation.claim_id, False, "locator_mismatch"
        )
    if normalize_quote(citation.quoted_text) not in normalize_document_text(chunk.text):
        return CitationVerification(
            citation.citation_id, citation.claim_id, False, "quote_not_literal"
        )
    return CitationVerification(citation.citation_id, citation.claim_id, True)


def verify_strategy_citations(
    strategy: StrategyVersion, chunks: Iterable[DocumentChunk]
) -> tuple[CitationVerification, ...]:
    """Verify every citation a strategy version carries, in declaration order."""

    by_id = {chunk.document_chunk_id: chunk for chunk in chunks}
    return tuple(verify_citation(citation, by_id) for citation in strategy.citations)


def citations_are_verified(results: Iterable[CitationVerification]) -> bool:
    """True only when every citation verified. An empty set is not verified."""

    checked = tuple(results)
    return bool(checked) and all(result.verified for result in checked)
