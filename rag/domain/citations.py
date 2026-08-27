"""Citation provenance verification (INV-24).

The automatic check answers one narrow question: does the citation name a chunk
that was actually retrieved, unchanged, at the locator it claims. Whether that
fragment supports the claim is a judgement the `evidence_reviewer` makes; no
code decides it.

`quoted_text` is a paraphrase and is deliberately *not* checked against the
chunk. That is a design decision, not an oversight: the draft is written to be
read by a caregiver, so the model rephrases in its own words and attributes the
idea to its source (see `authoring_draft.v0_5_0.json`). The guarantee that
survives is provenance — the cited document exists and was retrieved — not
literal quotation. Reintroducing a substring check here would make every
paraphrased draft abstain.

A provenance mismatch still blocks activation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from packages.shared.domain.rag import DocumentChunk, StrategyCitation, StrategyVersion

VerificationFailure = Literal[
    "chunk_unknown",
    "chunk_hash_mismatch",
    "locator_mismatch",
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
    """Check one citation's provenance against the chunk it names."""

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
