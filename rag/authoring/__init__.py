"""Offline authoring: index, retrieve, optionally draft, verify, review (SPEC 9.4).

`rag/authoring` never touches the clinical database and never sees a subject, an
observation or an outcome. It works on versioned literature and on generalised
questions that a privacy reviewer certified as carrying no case attributes.

The optional local draft is the only LLM in the system, and its output is a
draft: nothing here activates anything.
"""

from rag.authoring.bm25 import (
    BM25_B,
    BM25_K1,
    BM25_VERSION,
    TOKENIZER_VERSION,
    Bm25Index,
    ScoredChunk,
    tokenize,
)
from rag.authoring.build import (
    DEFAULT_CHUNK_PLAN,
    AuthoringBuild,
    build_authoring_corpus,
    chunk_lookup,
    library_versions,
)
from rag.authoring.drafting import (
    AUTHORING_DRAFT_PROMPT_FILE,
    PROMPT_PACKAGE,
    DraftRequest,
    DraftResult,
    DraftTransport,
    DraftUnavailableError,
    PromptTemplate,
    load_prompt,
    render_fragments,
    request_draft,
)
from rag.authoring.fusion import FusedChunk, reciprocal_rank_fusion
from rag.authoring.retrieval import (
    DenseModelNotRegisteredError,
    DenseRetriever,
    RetrievalPlan,
    RetrievalResult,
    ranked_chunk_hashes,
    resolve_retrieval_mode,
    retrieve,
)

__all__ = [
    "AUTHORING_DRAFT_PROMPT_FILE",
    "BM25_B",
    "BM25_K1",
    "BM25_VERSION",
    "DEFAULT_CHUNK_PLAN",
    "PROMPT_PACKAGE",
    "TOKENIZER_VERSION",
    "AuthoringBuild",
    "Bm25Index",
    "DenseModelNotRegisteredError",
    "DenseRetriever",
    "DraftRequest",
    "DraftResult",
    "DraftTransport",
    "DraftUnavailableError",
    "FusedChunk",
    "PromptTemplate",
    "RetrievalPlan",
    "RetrievalResult",
    "ScoredChunk",
    "build_authoring_corpus",
    "chunk_lookup",
    "library_versions",
    "load_prompt",
    "ranked_chunk_hashes",
    "reciprocal_rank_fusion",
    "render_fragments",
    "request_draft",
    "resolve_retrieval_mode",
    "retrieve",
    "tokenize",
]
