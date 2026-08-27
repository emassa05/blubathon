"""A document becomes indexable only with version, rights and hashes.

The failure mode this module exists to prevent is quiet: a PDF that is publicly
reachable gets treated as a licensed source, ends up in the index, and a claim
is later published against it. So `rights_basis` is never inferred, an
undeclared one raises, and a retired or withdrawn version can never enter a
corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from packages.shared.canonical import bytes_hash
from packages.shared.domain.rag import CorpusVersion, DocumentVersion
from packages.shared.enums import DocumentStatus
from rag.domain.hashing import CORPUS_ARTIFACT, seal
from rag.domain.normalization import normalize_document_text

EXTRACTOR_VERSION: Final = "extractor-plaintext-0.3.0"

RETIRED_DOCUMENT_STATUSES: Final[frozenset[DocumentStatus]] = frozenset(
    {DocumentStatus.SUPERSEDED, DocumentStatus.WITHDRAWN}
)

_UNDECLARED: Final = "undeclared"


class RightsNotDeclaredError(ValueError):
    """A source without verified reuse terms. It is not a corpus document."""


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """What the team actually has before anything is indexed.

    `original_bytes` is the file as downloaded; `extracted_text` is what the
    declared extractor produced from it. Both are hashed, because provenance and
    citation verification are different questions.
    """

    source_id: UUID
    publisher: str
    title: str
    document_version: str
    publication_date: str
    retrieved_at: datetime
    canonical_url: str
    rights_basis: str
    language: str
    original_bytes: bytes
    extracted_text: str

    @property
    def normalized_text(self) -> str:
        return normalize_document_text(self.extracted_text)


def build_document_version(
    document: SourceDocument,
    *,
    document_version_id: UUID,
    extraction_manifest_id: UUID,
    status: DocumentStatus = DocumentStatus.VERIFIED,
) -> DocumentVersion:
    """Hash the bytes and the normalised text, or refuse to build the version."""

    if not document.rights_basis.strip() or document.rights_basis == _UNDECLARED:
        raise RightsNotDeclaredError(
            f"{document.publisher} {document.document_version}: reuse terms are not declared, "
            "so this version cannot be indexed"
        )
    return DocumentVersion(
        document_version_id=document_version_id,
        source_id=document.source_id,
        publisher=document.publisher,
        title=document.title,
        document_version=document.document_version,
        publication_date=document.publication_date,
        retrieved_at=document.retrieved_at,
        canonical_url=document.canonical_url,
        rights_basis=document.rights_basis,
        original_bytes_sha256=bytes_hash(document.original_bytes),
        extracted_text_sha256=bytes_hash(document.normalized_text.encode("utf-8")),
        extraction_manifest_id=extraction_manifest_id,
        language=document.language,
        status=status,
    )


def is_indexable(document: DocumentVersion) -> bool:
    """A version that may back a chunk and therefore a citation."""

    return document.status not in RETIRED_DOCUMENT_STATUSES


def build_corpus_version(
    documents: tuple[DocumentVersion, ...],
    *,
    corpus_version: str,
    authoring_build_manifest_id: UUID,
    created_at: datetime,
) -> CorpusVersion:
    """The exact, ordered set of document versions a catalogue was built from."""

    if not documents:
        raise ValueError("a corpus version names at least one document version")
    retired = [document for document in documents if not is_indexable(document)]
    if retired:
        raise ValueError(
            "a corpus version cannot include a superseded or withdrawn document version"
        )
    ordered = tuple(sorted((document.document_version_id for document in documents), key=str))
    payload = {
        "corpus_version": corpus_version,
        "document_version_ids": [str(value) for value in ordered],
        "authoring_build_manifest_id": str(authoring_build_manifest_id),
        "created_at": created_at,
    }
    return CorpusVersion(
        corpus_version=corpus_version,
        document_version_ids=ordered,
        authoring_build_manifest_id=authoring_build_manifest_id,
        created_at=created_at,
        content_sha256=seal(payload, CORPUS_ARTIFACT),
    )
