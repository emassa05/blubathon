"""Local authoring CLI (TAREAS P1.6, H4).

Authoring is offline work with a CLI, not a public endpoint (SPEC 11.1). Three
commands:

``status``
    Reads the M0 candidate manifests and reports what the pipeline resolves to
    today: which retrieval mode a build would declare, and which SPEC 9.6
    readiness reason the runtime would abstain with. With no document holding a
    verified rights basis the answer is `corpus_not_ready`, and that is the
    honest answer, not a failure to fix.
``build``
    Builds chunks, a lexical index, a corpus version and a build manifest from a
    directory of rights-cleared documents, and writes only manifests and hashes.
    Document bodies, extracted text and indices never enter Git.
``manifest``
    Writes `data/rag-build.manifest.json`, the M4 handoff: every version and
    hash that fixes a retrieval result, plus the declared corpus and catalogue
    status. It is generated, not typed, so it cannot drift from the code.
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from packages.shared.constants import (
    MAX_RUNTIME_STRATEGIES,
    RAG_DENSE_TOP_K,
    RAG_FINAL_CHUNKS,
    RAG_LEXICAL_TOP_K,
    RAG_RRF_K,
    RUNTIME_LLM_CALLS,
    SPEC_VERSION,
    STRATEGY_REQUIRED_DISTINCT_REVIEWERS,
)
from packages.shared.domain.rag import resolve_catalog_readiness
from packages.shared.enums import CatalogReadiness, RetrievalMode
from rag.authoring.bm25 import BM25_B, BM25_K1, BM25_VERSION, TOKENIZER_VERSION
from rag.authoring.build import DEFAULT_CHUNK_PLAN, build_authoring_corpus
from rag.authoring.drafting import load_prompt
from rag.authoring.retrieval import RetrievalPlan
from rag.domain.documents import EXTRACTOR_VERSION, RightsNotDeclaredError, SourceDocument
from rag.domain.hashing import RAG_SCHEMA_VERSION
from rag.domain.normalization import NORMALIZATION_VERSION

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]
DATA_DIR: Final = REPOSITORY_ROOT / "data"
CORPUS_CANDIDATES: Final = DATA_DIR / "corpus-candidates.manifest.json"
MODEL_CANDIDATES: Final = DATA_DIR / "model-candidates.manifest.json"

SOURCE_SUFFIX: Final = ".source.json"
BUILD_NAMESPACE: Final = uuid.UUID("6f1f3a2e-5c4d-4b8a-9f0e-7d6c5b4a3928")


def _identifier(label: str) -> uuid.UUID:
    """A stable, v4-shaped identifier so a rebuild produces the same ids."""

    raw = bytearray(uuid.uuid5(BUILD_NAMESPACE, label).bytes)
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolved_retrieval_mode(model_manifest: dict[str, Any]) -> RetrievalMode:
    """Hybrid only when an embedding model is registered with licence and hash."""

    registered = model_manifest.get("embedding_models") or []
    return RetrievalMode.HYBRID if registered else RetrievalMode.LEXICAL_ONLY


def cleared_documents(corpus_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Documents whose reuse terms the team actually verified."""

    return [
        document
        for document in corpus_manifest.get("documents") or []
        if document.get("rights_status") == "cleared" and document.get("rights_basis")
    ]


def status_report(
    corpus_manifest: dict[str, Any], model_manifest: dict[str, Any]
) -> dict[str, Any]:
    """What a build and the runtime would do with today's declared state."""

    documents = cleared_documents(corpus_manifest)
    readiness = resolve_catalog_readiness(
        corpus_available=bool(documents),
        # No accredited clinical reviewer exists while the corpus is blocked, so
        # the precedence never reaches that branch; it is stated, not guessed.
        blocked_only_by_clinical_review=False,
        dependency_suspended=False,
        active_catalog_count=0,
    )
    mode = resolved_retrieval_mode(model_manifest)
    return {
        "corpus_status": corpus_manifest.get("status"),
        "cleared_document_count": len(documents),
        "retrieval_mode": mode.value,
        "retrieval_mode_reason": model_manifest.get("resolved_build_mode_reason"),
        "runtime_llm_calls": 0,
        "catalog_readiness": (
            CatalogReadiness.READY.value if readiness is None else readiness.value
        ),
        "catalog_status": "blocked_corpus" if not documents else "not_ready",
        "consequences": corpus_manifest.get("consequences", []),
    }


BUILD_MANIFEST_PATH: Final = DATA_DIR / "rag-build.manifest.json"


def build_status_manifest(
    corpus_manifest: dict[str, Any], model_manifest: dict[str, Any]
) -> dict[str, Any]:
    """The M4 handoff (TAREAS H4): versions, hashes and declared status.

    Everything that could change a retrieval result is named here, so P2 can
    cite the exact pipeline without holding any corpus body, index or model.
    """

    status = status_report(corpus_manifest, model_manifest)
    prompt = load_prompt()
    return {
        "manifest_kind": "rag_build",
        "manifest_version": "1",
        "spec_version": SPEC_VERSION,
        "schema_version": RAG_SCHEMA_VERSION,
        "purpose": (
            "TAREAS M4/H4 - the authoring pipeline this repository would run today, with the "
            "versions and hashes that fix its result. No corpus body, index or model is tracked."
        ),
        "retrieval_mode": status["retrieval_mode"],
        "retrieval_mode_reason": status["retrieval_mode_reason"],
        "pipeline": {
            "extractor_version": EXTRACTOR_VERSION,
            "ocr_version": None,
            "normalization_version": NORMALIZATION_VERSION,
            "chunker_version": DEFAULT_CHUNK_PLAN.chunker_version,
            "chunk_size": DEFAULT_CHUNK_PLAN.chunk_size,
            "chunk_overlap": DEFAULT_CHUNK_PLAN.chunk_overlap,
            "tokenizer_version": TOKENIZER_VERSION,
            "bm25_version": BM25_VERSION,
            "bm25_parameters": {"k1": BM25_K1, "b": BM25_B},
            "lexical_top_k": RAG_LEXICAL_TOP_K,
            "dense_top_k": RAG_DENSE_TOP_K,
            "rrf_k": RAG_RRF_K,
            "final_chunk_count": RAG_FINAL_CHUNKS,
            "prompt_version": prompt.prompt_version,
            "prompt_sha256": prompt.prompt_sha256,
        },
        "runtime": {
            "llm_calls": RUNTIME_LLM_CALLS,
            "max_strategies": MAX_RUNTIME_STRATEGIES,
            "required_distinct_reviewers": STRATEGY_REQUIRED_DISTINCT_REVIEWERS,
        },
        "corpus_status": status["corpus_status"],
        "cleared_document_count": status["cleared_document_count"],
        "corpus_versions": [],
        "catalog_versions": [],
        "catalog_readiness": status["catalog_readiness"],
        "catalog_status": (
            "blocked_corpus" if status["cleared_document_count"] == 0 else "not_ready"
        ),
        "consequences": status["consequences"],
    }


def load_sources(corpus_dir: Path) -> list[SourceDocument]:
    """Read `*.source.json` declarations and the plain text they point at."""

    sources: list[SourceDocument] = []
    for path in sorted(corpus_dir.glob(f"*{SOURCE_SUFFIX}")):
        declaration = _read_json(path)
        text_path = corpus_dir / declaration["text_file"]
        raw = text_path.read_bytes()
        sources.append(
            SourceDocument(
                source_id=uuid.UUID(declaration["source_id"]),
                publisher=declaration["publisher"],
                title=declaration["title"],
                document_version=declaration["document_version"],
                publication_date=declaration["publication_date"],
                retrieved_at=datetime.fromisoformat(declaration["retrieved_at"]),
                canonical_url=declaration["canonical_url"],
                rights_basis=declaration.get("rights_basis", "undeclared"),
                language=declaration["language"],
                original_bytes=raw,
                extracted_text=raw.decode("utf-8"),
            )
        )
    return sources


def build_report(build: Any) -> dict[str, Any]:
    """Manifests and hashes only. Bodies and indices stay out of the report."""

    return {
        "manifest": build.manifest.model_dump(mode="json"),
        "corpus": build.corpus.model_dump(mode="json"),
        "documents": [
            {
                "document_version_id": str(document.document_version_id),
                "publisher": document.publisher,
                "document_version": document.document_version,
                "rights_basis": document.rights_basis,
                "original_bytes_sha256": document.original_bytes_sha256,
                "extracted_text_sha256": document.extracted_text_sha256,
                "status": document.status.value,
            }
            for document in build.documents
        ],
        "chunks": [
            {
                "document_chunk_id": str(chunk.document_chunk_id),
                "document_version_id": str(chunk.document_version_id),
                "locator": chunk.locator,
                "chunk_sha256": chunk.chunk_sha256,
                "chunker_version": chunk.chunker_version,
            }
            for chunk in build.chunks
        ],
    }


def run_build(corpus_dir: Path, out_dir: Path, *, corpus_version: str) -> int:
    sources = load_sources(corpus_dir)
    if not sources:
        print(
            json.dumps(
                {"status": "blocked", "reason": "corpus_not_ready", "documents": 0}, indent=2
            )
        )
        return 1
    try:
        build = build_authoring_corpus(
            sources,
            corpus_version=corpus_version,
            id_for=_identifier,
            built_at=datetime.now(UTC),
            chunk_plan=DEFAULT_CHUNK_PLAN,
            retrieval_plan=RetrievalPlan.lexical_only(),
        )
    except RightsNotDeclaredError as error:
        print(json.dumps({"status": "blocked", "reason": "corpus_not_ready", "detail": str(error)}))
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(build)
    (out_dir / "build.manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "built",
                "retrieval_mode": build.manifest.retrieval_mode.value,
                "documents": len(build.documents),
                "chunks": len(build.chunks),
                "corpus_version": build.corpus.corpus_version,
                "manifest_sha256": build.manifest.content_sha256,
                "catalog_status": "blocked_clinical_review",
            },
            indent=2,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.rag_authoring", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="report corpus, model and catalogue readiness")
    manifest = commands.add_parser("manifest", help="write the H4 build manifest")
    manifest.add_argument("--out", type=Path, default=BUILD_MANIFEST_PATH)

    build = commands.add_parser("build", help="build chunks, index, corpus and manifest")
    build.add_argument("--corpus-dir", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--corpus-version", default="corpus-0.3.0")

    args = parser.parse_args(argv)
    if args.command == "status":
        report = status_report(_read_json(CORPUS_CANDIDATES), _read_json(MODEL_CANDIDATES))
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "manifest":
        payload = build_status_manifest(_read_json(CORPUS_CANDIDATES), _read_json(MODEL_CANDIDATES))
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
        return 0
    return run_build(args.corpus_dir, args.out, corpus_version=args.corpus_version)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
