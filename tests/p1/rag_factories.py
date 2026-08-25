"""Fictional authoring fixtures for the P1 RAG tests.

Nothing here is a real guideline, a real licence or a real clinical claim. The
text is invented for the tests, the publisher name is a placeholder, and the
rights basis says so. That is deliberate: SPEC 20 and TAREAS M0 forbid inventing
a citation or an approval to make a test pass, so these fixtures exist to prove
the machinery, never to stand in for evidence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from packages.shared.domain.identity import ProfessionalAccreditation
from packages.shared.domain.rag import (
    AuthoringReview,
    CatalogVersion,
    DocumentChunk,
    RecommendationSetVersion,
    ScenarioPredicate,
    ScenarioV1,
    StrategyCitation,
    StrategyClaim,
    StrategyVersion,
)
from packages.shared.enums import (
    AccreditationCapability,
    AuthoringReviewDecision,
    AuthoringReviewKind,
    AuthoringReviewObjectType,
    AuthorizationStatus,
    CatalogStatus,
    DocumentStatus,
    FieldCode,
    Role,
    StrategyStatus,
)
from rag.authoring.build import AuthoringBuild, build_authoring_corpus
from rag.authoring.retrieval import RetrievalPlan
from rag.domain.activation import (
    catalog_content_sha256,
    set_content_sha256,
    strategy_content_sha256,
)
from rag.domain.chunking import ChunkPlan
from rag.domain.documents import SourceDocument
from tests.p1.factories import TENANT, ident

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


def accreditation(
    label: str, *, capabilities: frozenset[AccreditationCapability]
) -> ProfessionalAccreditation:
    return ProfessionalAccreditation(
        accreditation_id=ident(f"accreditation:{label}"),
        tenant_id=TENANT,
        actor_id=ident(f"actor:{label}"),
        capabilities=capabilities,
        credential_policy_version="accreditation-0.3.0",
        issuer_actor_id=ident("actor:tenant-admin"),
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        status=AuthorizationStatus.ACTIVE,
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def review(
    label: str,
    *,
    actor_label: str,
    object_type: AuthoringReviewObjectType,
    object_version_id: uuid.UUID,
    review_kind: AuthoringReviewKind,
    content_sha256: str,
    decision: AuthoringReviewDecision = AuthoringReviewDecision.APPROVED,
    reviewed_at: datetime = BUILT_AT,
) -> AuthoringReview:
    return AuthoringReview(
        authoring_review_id=ident(f"review:{label}"),
        tenant_id=TENANT,
        object_type=object_type,
        object_version_id=object_version_id,
        review_kind=review_kind,
        actor_id=ident(f"actor:{actor_label}"),
        accreditation_id=ident(f"accreditation:{actor_label}"),
        decision=decision,
        reviewed_content_sha256=content_sha256,
        reviewed_at=reviewed_at,
        ingested_at=reviewed_at,
    )


def strategy(
    label: str,
    *,
    build: AuthoringBuild,
    quote: str,
    action_text: str,
    claim_text: str,
    predicate: ScenarioPredicate,
    status: StrategyStatus = StrategyStatus.ACTIVE,
    evidence_review_id: uuid.UUID | None = None,
    clinical_review_id: uuid.UUID | None = None,
    effective_from: datetime = BUILT_AT,
) -> StrategyVersion:
    """A strategy version whose claim, citation and content hash all line up."""

    chunk = chunk_containing(build, quote)
    claim_id = ident(f"claim:{label}")
    citation = StrategyCitation(
        citation_id=ident(f"citation:{label}"),
        claim_id=claim_id,
        document_chunk_id=chunk.document_chunk_id,
        locator=chunk.locator,
        quoted_text=quote,
        chunk_sha256=chunk.chunk_sha256,
        canonical_url="https://example.invalid/fixtures/quoted",
    )
    start = action_text.index(claim_text)
    claim = StrategyClaim(
        claim_id=claim_id,
        start=start,
        end=start + len(claim_text),
        claim_text_es=claim_text,
        citation_ids=(citation.citation_id,),
    )
    content = {
        "strategy_id": ident(f"strategy:{label}"),
        "strategy_version_id": ident(f"strategy-version:{label}"),
        "purpose_es": f"Proposito de prueba {label}.",
        "action_text_es": action_text,
        "claims": (claim,),
        "citations": (citation,),
        "applicability_predicate": predicate,
        "required_approver_role": Role.PROFESSIONAL,
        "allowed_executor_roles": frozenset({Role.CAREGIVER, Role.PROFESSIONAL}),
        "corpus_version": build.corpus.corpus_version,
        "effective_from": effective_from,
    }
    # The content hash covers the reviewed content, so it is computed once from
    # a draft and then carried unchanged into whatever state the fixture needs.
    sealed = strategy_content_sha256(
        StrategyVersion(**content, status=StrategyStatus.DRAFT, content_sha256="0" * 64)
    )
    return StrategyVersion(
        **content,
        status=status,
        evidence_review_id=evidence_review_id,
        clinical_review_id=clinical_review_id,
        content_sha256=sealed,
    )


def recommendation_set(
    label: str,
    *,
    strategy_version_ids: tuple[uuid.UUID, ...],
    predicate: ScenarioPredicate,
    reviewed_priority: int = 0,
    status: CatalogStatus = CatalogStatus.ACTIVE,
    clinical_review_id: uuid.UUID | None = None,
    effective_from: datetime = BUILT_AT,
    suspended_at: datetime | None = None,
) -> RecommendationSetVersion:
    content = {
        "recommendation_set_id": ident(f"set:{label}"),
        "recommendation_set_version": f"set-{label}-1",
        "applicability_predicate": predicate,
        "ordered_strategy_version_ids": strategy_version_ids,
        "reviewed_priority": reviewed_priority,
        "effective_from": effective_from,
    }
    sealed = set_content_sha256(
        RecommendationSetVersion(**content, status=CatalogStatus.DRAFT, content_sha256="0" * 64)
    )
    return RecommendationSetVersion(
        **content,
        status=status,
        clinical_review_id=clinical_review_id,
        suspended_at=suspended_at,
        content_sha256=sealed,
    )


def catalog(
    label: str,
    *,
    build: AuthoringBuild,
    set_ids: tuple[uuid.UUID, ...],
    status: CatalogStatus = CatalogStatus.ACTIVE,
    activation_review_id: uuid.UUID | None = None,
    effective_from: datetime = BUILT_AT,
    suspended_at: datetime | None = None,
) -> CatalogVersion:
    content = {
        "catalog_version": f"catalog-{label}-1",
        "tenant_id": TENANT,
        "corpus_version": build.corpus.corpus_version,
        "recommendation_set_version_ids": set_ids,
        "effective_from": effective_from,
    }
    sealed = catalog_content_sha256(
        CatalogVersion(**content, status=CatalogStatus.DRAFT, content_sha256="0" * 64)
    )
    return CatalogVersion(
        **content,
        status=status,
        catalog_activation_review_id=activation_review_id,
        suspended_at=suspended_at,
        content_sha256=sealed,
    )


def scenario(**field_values: str) -> ScenarioV1:
    return ScenarioV1(
        field_values={FieldCode(code): value for code, value in field_values.items()},
        context_tags=("home",),
    )
