"""One reproducible authoring build (SPEC 9.4, TAREAS P1.6).

A build turns a set of rights-cleared documents into hashed chunks, a lexical
index, a corpus version and a manifest that fixes everything capable of changing
a retrieval result: extractor, normalisation, chunker, tokenizer, BM25
parameters, the dense model when there is one, RRF, the prompt, the libraries
and the platform.

The build is the place where the free-text veto is enforced rather than
described: only text carrying an authorised document version reaches the
chunker, and therefore the index and the prompt (SPEC 2.23, INV-22).
"""

from __future__ import annotations

import platform as platform_module
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from packages.shared.constants import CONTRACT_VERSION
from packages.shared.domain.rag import (
    AuthoringBuildManifest,
    CorpusVersion,
    DocumentChunk,
    DocumentVersion,
)
from packages.shared.enums import DocumentStatus, RetrievalMode
from rag.authoring.bm25 import BM25_VERSION, TOKENIZER_VERSION, Bm25Index
from rag.authoring.drafting import PromptTemplate
from rag.authoring.retrieval import DenseRetriever, RetrievalPlan
from rag.domain.chunking import ChunkPlan, chunk_document
from rag.domain.documents import (
    EXTRACTOR_VERSION,
    SourceDocument,
    build_corpus_version,
    build_document_version,
)
from rag.domain.hashing import MANIFEST_ARTIFACT, seal
from rag.domain.normalization import NORMALIZATION_VERSION
from rag.domain.text_guard import assert_literature_only, literature

DEFAULT_CHUNK_PLAN: Final = ChunkPlan(chunk_size=220, chunk_overlap=40)


@dataclass(frozen=True, slots=True)
class AuthoringBuild:
    """Everything one build produced, ready to be reviewed and hashed."""

    manifest: AuthoringBuildManifest
    corpus: CorpusVersion
    documents: tuple[DocumentVersion, ...]
    chunks: tuple[DocumentChunk, ...]
    index: Bm25Index

    @property
    def authorised_document_version_ids(self) -> frozenset[UUID]:
        return frozenset(document.document_version_id for document in self.documents)


def library_versions() -> dict[str, str]:
    """The versions that can move a ranking, recorded with the build."""

    return {
        "python": sys.version.split()[0],
        "faro_contract": CONTRACT_VERSION,
        "bm25": BM25_VERSION,
        "tokenizer": TOKENIZER_VERSION,
    }


def build_authoring_corpus(
    sources: Sequence[SourceDocument],
    *,
    corpus_version: str,
    id_for: Callable[[str], UUID],
    built_at: datetime,
    chunk_plan: ChunkPlan = DEFAULT_CHUNK_PLAN,
    retrieval_plan: RetrievalPlan | None = None,
    dense: DenseRetriever | None = None,
    prompt: PromptTemplate | None = None,
    platform_label: str | None = None,
    libraries: dict[str, str] | None = None,
    document_status: DocumentStatus = DocumentStatus.INDEXED,
) -> AuthoringBuild:
    """Build the corpus, chunks, index and manifest for one authoring run."""

    if not sources:
        raise ValueError("an authoring build needs at least one rights-cleared document")

    plan = retrieval_plan or (
        RetrievalPlan(mode=RetrievalMode.HYBRID)
        if dense is not None
        else RetrievalPlan.lexical_only()
    )
    if plan.mode is RetrievalMode.HYBRID and dense is None:
        raise ValueError("a hybrid build declares a registered dense model")

    documents: list[DocumentVersion] = []
    chunks: list[DocumentChunk] = []
    for source in sources:
        document_version_id = id_for(f"document:{source.source_id}:{source.document_version}")
        document = build_document_version(
            source,
            document_version_id=document_version_id,
            extraction_manifest_id=id_for(f"extraction:{corpus_version}"),
            status=document_status,
        )
        documents.append(document)
        # The guard runs before the chunker, not after it: the point is that
        # nothing but authorised literature ever becomes a fragment.
        assert_literature_only(
            (literature(source.normalized_text, document_version_id),),
            authorised=frozenset({document_version_id}),
        )
        chunks.extend(
            chunk_document(
                document_version_id=document_version_id,
                text=source.normalized_text,
                plan=chunk_plan,
                chunk_id_for=lambda locator, key=str(document_version_id): id_for(
                    f"chunk:{key}:{locator}"
                ),
            )
        )

    index = Bm25Index(chunks)
    manifest_id = id_for(f"manifest:{corpus_version}")
    payload = {
        "authoring_build_manifest_id": str(manifest_id),
        "retrieval_mode": plan.mode.value,
        "extractor_version": EXTRACTOR_VERSION,
        "ocr_version": None,
        "normalization_version": NORMALIZATION_VERSION,
        "chunker_version": chunk_plan.chunker_version,
        "chunk_size": chunk_plan.chunk_size,
        "chunk_overlap": chunk_plan.chunk_overlap,
        "tokenizer_version": TOKENIZER_VERSION,
        "bm25_parameters": index.parameters,
        "lexical_top_k": plan.lexical_top_k,
        "dense_model_id": dense.model_id if dense is not None else None,
        "dense_model_sha256": dense.model_sha256 if dense is not None else None,
        "dense_top_k": plan.dense_top_k,
        "rrf_k": plan.rrf_k,
        "final_chunk_count": plan.final_chunk_count,
        "prompt_version": prompt.prompt_version if prompt is not None else None,
        "prompt_sha256": prompt.prompt_sha256 if prompt is not None else None,
        "library_versions": libraries or library_versions(),
        "platform": platform_label or platform_module.platform(),
        "built_at": built_at,
        "chunk_sha256_list": sorted(chunk.chunk_sha256 for chunk in chunks),
    }
    manifest = AuthoringBuildManifest(
        authoring_build_manifest_id=manifest_id,
        retrieval_mode=plan.mode,
        extractor_version=EXTRACTOR_VERSION,
        ocr_version=None,
        normalization_version=NORMALIZATION_VERSION,
        chunker_version=chunk_plan.chunker_version,
        chunk_size=chunk_plan.chunk_size,
        chunk_overlap=chunk_plan.chunk_overlap,
        tokenizer_version=TOKENIZER_VERSION,
        bm25_parameters=index.parameters,
        lexical_top_k=plan.lexical_top_k,
        dense_model_id=dense.model_id if dense is not None else None,
        dense_model_sha256=dense.model_sha256 if dense is not None else None,
        dense_top_k=plan.dense_top_k,
        rrf_k=plan.rrf_k,
        final_chunk_count=plan.final_chunk_count,
        prompt_version=prompt.prompt_version if prompt is not None else None,
        library_versions=payload["library_versions"],
        platform=payload["platform"],
        built_at=built_at,
        content_sha256=seal(payload, MANIFEST_ARTIFACT),
    )
    corpus = build_corpus_version(
        tuple(documents),
        corpus_version=corpus_version,
        authoring_build_manifest_id=manifest_id,
        created_at=built_at,
    )
    return AuthoringBuild(
        manifest=manifest,
        corpus=corpus,
        documents=tuple(documents),
        chunks=tuple(chunks),
        index=index,
    )


def chunk_lookup(chunks: Iterable[DocumentChunk]) -> dict[UUID, DocumentChunk]:
    return {chunk.document_chunk_id: chunk for chunk in chunks}
