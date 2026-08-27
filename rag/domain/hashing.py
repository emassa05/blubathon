"""Domain separators for every hashed authoring artifact.

Two artifacts that mean the same thing hash the same, two that differ do not,
and a document hash can never collide with a strategy hash. `seal` exists
because a content hash covers everything *except* the field it is written into.
"""

from __future__ import annotations

from typing import Any, Final

from packages.shared.canonical import content_hash

RAG_SCHEMA_VERSION: Final = "rag-0.3.0"
"""Schema version of every authoring artifact hashed by this package."""

DOCUMENT_ARTIFACT: Final = "document_version"
CHUNK_ARTIFACT: Final = "document_chunk"
CORPUS_ARTIFACT: Final = "corpus_version"
MANIFEST_ARTIFACT: Final = "authoring_build_manifest"
STRATEGY_ARTIFACT: Final = "strategy_version"
SET_ARTIFACT: Final = "recommendation_set_version"
CATALOG_ARTIFACT: Final = "catalog_version"

CONTENT_HASH_FIELD: Final = "content_sha256"


def seal(payload: dict[str, Any], artifact: str, schema_version: str = RAG_SCHEMA_VERSION) -> str:
    """Domain-separated hash of a payload, excluding its own content hash field.

    A reviewer approves a payload, not the digest printed on it, so the digest
    is computed over everything else and then written in.
    """

    body = {key: value for key, value in payload.items() if key != CONTENT_HASH_FIELD}
    return content_hash(artifact, schema_version, body)
