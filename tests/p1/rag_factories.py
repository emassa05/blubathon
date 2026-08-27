"""Fictional authoring fixtures for the P1 RAG tests.

Nothing here is a real guideline, a real licence or a real clinical claim. The
text is invented for the tests, the publisher name is a placeholder, and the
rights basis says so. That is deliberate: SPEC 20 and TAREAS M0 forbid inventing
a citation or an approval to make a test pass, so these fixtures exist to prove
the machinery, never to stand in for evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.shared.domain.rag import DocumentChunk
from packages.shared.enums import DocumentStatus
from rag.authoring.build import AuthoringBuild, build_authoring_corpus
from rag.authoring.retrieval import RetrievalPlan
from rag.domain.chunking import ChunkPlan
from rag.domain.documents import SourceDocument
from tests.p1.factories import ident

BUILT_AT = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

FIXTURE_RIGHTS = "fixture-only: invented text written for the tests, not a licensed source"

SLEEP_TEXT = """Rutina de sueno y ambiente

Una rutina previsible antes de dormir puede ayudar a que la persona anticipe lo
que viene. En este texto de prueba, la rutina se describe como una secuencia
estable de pasos cortos.

El ambiente sensorial tambien importa. Reducir el ruido y la luz intensa en la
hora previa se describe aqui como una medida de apoyo.

Nada de este parrafo constituye una recomendacion clinica real.
"""

GI_TEXT = """Molestias digestivas y regulacion

Este texto de prueba describe la relacion entre molestias digestivas y la
capacidad de participar en actividades. Se sugiere registrar el patron durante
varios dias antes de sacar conclusiones.

Registrar el patron durante varios dias permite distinguir un dia aislado de una
tendencia sostenida.
"""

SLEEP_QUOTE = "Reducir el ruido y la luz intensa en la\nhora previa"
GI_QUOTE = "Registrar el patron durante varios dias"

ACTION_TEXT_SLEEP = (
    "Manten una secuencia estable de pasos cortos antes de dormir y reduce el ruido y la luz "
    "intensa en la hora previa."
)
CLAIM_TEXT_SLEEP = "reduce el ruido y la luz intensa en la hora previa"

ACTION_TEXT_GI = "Registra el patron digestivo durante varios dias antes de cambiar la rutina."
CLAIM_TEXT_GI = "Registra el patron digestivo durante varios dias"


def source(label: str, text: str, *, rights_basis: str = FIXTURE_RIGHTS) -> SourceDocument:
    raw = text.encode("utf-8")
    return SourceDocument(
        source_id=ident(f"source:{label}"),
        publisher="Fixture Publisher",
        title=f"Fixture document {label}",
        document_version="1",
        publication_date="2026-01-15",
        retrieved_at=BUILT_AT,
        canonical_url=f"https://example.invalid/fixtures/{label}",
        rights_basis=rights_basis,
        language="es",
        original_bytes=raw,
        extracted_text=text,
    )


def fixture_build(
    *,
    sources: tuple[SourceDocument, ...] | None = None,
    chunk_plan: ChunkPlan | None = None,
) -> AuthoringBuild:
    """A lexical-only build over the fixture corpus, as M0 resolves today."""

    return build_authoring_corpus(
        sources or (source("sleep", SLEEP_TEXT), source("gi", GI_TEXT)),
        corpus_version="corpus-fixture-1",
        id_for=ident,
        built_at=BUILT_AT,
        chunk_plan=chunk_plan or ChunkPlan(chunk_size=60, chunk_overlap=10),
        retrieval_plan=RetrievalPlan.lexical_only(),
        platform_label="fixture-platform",
        libraries={"python": "fixture", "bm25": "fixture"},
        document_status=DocumentStatus.INDEXED,
    )


def chunk_containing(build: AuthoringBuild, quote: str) -> DocumentChunk:
    """The one fixture chunk that literally contains a quote."""

    for chunk in build.chunks:
        if quote in chunk.text:
            return chunk
    raise AssertionError(f"no fixture chunk contains {quote!r}")
