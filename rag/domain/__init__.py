"""What a document, chunk, citation, review and activation gate mean (SPEC 9.2-9.6).

Nothing in this package retrieves, ranks or drafts. It answers the questions the
authoring pipeline and the runtime both have to agree on: is this document
indexable, is this quote literal, did two distinct accredited people review it,
and may this version be served at all.
"""

from rag.domain.activation import (
    ActivationDecision,
    catalog_activation_decision,
    catalog_content_payload,
    catalog_content_sha256,
    catalog_review_subject,
    predicate_payload,
    set_activation_decision,
    set_content_payload,
    set_content_sha256,
    strategy_activation_decision,
    strategy_content_payload,
    strategy_content_sha256,
    suspended_by_dependency,
)
from rag.domain.chunking import (
    CHUNKER_VERSION,
    ChunkPlan,
    Paragraph,
    chunk_document,
    split_paragraphs,
)
from rag.domain.citations import (
    CitationVerification,
    citations_are_verified,
    verify_citation,
    verify_strategy_citations,
)
from rag.domain.documents import (
    EXTRACTOR_VERSION,
    RETIRED_DOCUMENT_STATUSES,
    RightsNotDeclaredError,
    SourceDocument,
    build_corpus_version,
    build_document_version,
    is_indexable,
)
from rag.domain.hashing import (
    CATALOG_ARTIFACT,
    CHUNK_ARTIFACT,
    CORPUS_ARTIFACT,
    DOCUMENT_ARTIFACT,
    MANIFEST_ARTIFACT,
    RAG_SCHEMA_VERSION,
    SET_ARTIFACT,
    STRATEGY_ARTIFACT,
    seal,
)
from rag.domain.normalization import (
    NORMALIZATION_VERSION,
    normalize_document_text,
    normalize_quote,
)
from rag.domain.reviews import REQUIRED_CAPABILITY, ReviewLedger, required_capability
from rag.domain.text_guard import (
    FREE_TEXT_FIELDS,
    FreeTextLeakError,
    TextProvenance,
    assert_literature_only,
    assert_no_clinical_text,
    literature,
)

__all__ = [
    "CATALOG_ARTIFACT",
    "CHUNKER_VERSION",
    "CHUNK_ARTIFACT",
    "CORPUS_ARTIFACT",
    "DOCUMENT_ARTIFACT",
    "EXTRACTOR_VERSION",
    "FREE_TEXT_FIELDS",
    "MANIFEST_ARTIFACT",
    "NORMALIZATION_VERSION",
    "RAG_SCHEMA_VERSION",
    "REQUIRED_CAPABILITY",
    "RETIRED_DOCUMENT_STATUSES",
    "SET_ARTIFACT",
    "STRATEGY_ARTIFACT",
    "ActivationDecision",
    "ChunkPlan",
    "CitationVerification",
    "FreeTextLeakError",
    "Paragraph",
    "ReviewLedger",
    "RightsNotDeclaredError",
    "SourceDocument",
    "TextProvenance",
    "assert_literature_only",
    "assert_no_clinical_text",
    "build_corpus_version",
    "build_document_version",
    "catalog_activation_decision",
    "catalog_content_payload",
    "catalog_content_sha256",
    "catalog_review_subject",
    "chunk_document",
    "citations_are_verified",
    "is_indexable",
    "literature",
    "normalize_document_text",
    "normalize_quote",
    "predicate_payload",
    "required_capability",
    "seal",
    "set_activation_decision",
    "set_content_payload",
    "set_content_sha256",
    "split_paragraphs",
    "strategy_activation_decision",
    "strategy_content_payload",
    "strategy_content_sha256",
    "suspended_by_dependency",
    "verify_citation",
    "verify_strategy_citations",
]
