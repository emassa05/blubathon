"""Deterministic chunking that keeps a citation literal and locatable (SPEC 9.3).

Every chunk is a contiguous span of whole paragraphs of the normalised document,
so its text is a verbatim substring of that document and its locator names the
exact paragraphs a reviewer can open. A paragraph is never split in the middle,
even when it alone exceeds the size budget: a citation that straddles an
arbitrary cut is not something a human can verify.

Size and overlap are counted in tokens of the declared tokenizer, and both, with
the tokenizer version, are fixed and hashed in the build manifest (SPEC 9.4).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from packages.shared.domain.rag import DocumentChunk
from rag.domain.hashing import CHUNK_ARTIFACT, seal
from rag.domain.normalization import normalize_document_text

CHUNKER_VERSION: Final = "chunker-paragraph-0.3.0"

_PARAGRAPH_BREAK: Final = re.compile(r"\n[ \t]*\n")
_TOKEN: Final = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Paragraph:
    """One paragraph with its 1-based index and its span in the normalised text."""

    index: int
    start: int
    end: int
    text: str

    @property
    def token_count(self) -> int:
        return len(_TOKEN.findall(self.text))


@dataclass(frozen=True, slots=True)
class ChunkPlan:
    """Size budget and overlap, both in tokens of the declared tokenizer."""

    chunk_size: int
    chunk_overlap: int
    chunker_version: str = CHUNKER_VERSION

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk overlap must be smaller than chunk size")


def split_paragraphs(text: str) -> tuple[Paragraph, ...]:
    """Paragraphs of the normalised text, in order, with their exact spans."""

    normalized = normalize_document_text(text)
    breaks = [*_PARAGRAPH_BREAK.finditer(normalized), None]
    paragraphs: list[Paragraph] = []
    cursor = 0
    for match in breaks:
        end = len(normalized) if match is None else match.start()
        segment = normalized[cursor:end]
        body = segment.strip()
        if body:
            start = cursor + (len(segment) - len(segment.lstrip()))
            paragraphs.append(
                Paragraph(
                    index=len(paragraphs) + 1,
                    start=start,
                    end=start + len(body),
                    text=body,
                )
            )
        cursor = end if match is None else match.end()
    return tuple(paragraphs)


def _locator(members: list[Paragraph]) -> str:
    if len(members) == 1:
        return f"paragraph {members[0].index}"
    return f"paragraphs {members[0].index}-{members[-1].index}"


def _group(paragraphs: tuple[Paragraph, ...], plan: ChunkPlan) -> list[list[Paragraph]]:
    groups: list[list[Paragraph]] = []
    current: list[Paragraph] = []
    budget = 0
    for paragraph in paragraphs:
        tokens = paragraph.token_count
        if current and budget + tokens > plan.chunk_size:
            groups.append(current)
            carried: list[Paragraph] = []
            carried_tokens = 0
            for previous in reversed(current):
                if carried_tokens + previous.token_count > plan.chunk_overlap:
                    break
                carried.insert(0, previous)
                carried_tokens += previous.token_count
            current = [*carried, paragraph]
            budget = carried_tokens + tokens
            continue
        current.append(paragraph)
        budget += tokens
    if current:
        groups.append(current)
    return groups


def chunk_document(
    *,
    document_version_id: UUID,
    text: str,
    plan: ChunkPlan,
    chunk_id_for: Callable[[str], UUID],
) -> tuple[DocumentChunk, ...]:
    """Chunk one document version into locatable, hashed, verbatim fragments.

    `chunk_id_for` maps a locator to the identifier the caller persists, so the
    same build over the same document produces the same identifiers.
    """

    normalized = normalize_document_text(text)
    paragraphs = split_paragraphs(normalized)
    if not paragraphs:
        return ()

    chunks: list[DocumentChunk] = []
    for members in _group(paragraphs, plan):
        body = normalized[members[0].start : members[-1].end]
        locator = _locator(members)
        payload = {
            "document_version_id": str(document_version_id),
            "locator": locator,
            "text": body,
            "chunker_version": plan.chunker_version,
        }
        chunks.append(
            DocumentChunk(
                document_chunk_id=chunk_id_for(locator),
                document_version_id=document_version_id,
                locator=locator,
                text=body,
                chunk_sha256=seal(payload, CHUNK_ARTIFACT),
                chunker_version=plan.chunker_version,
            )
        )
    return tuple(chunks)
