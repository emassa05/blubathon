"""Activation gates for strategies, sets and catalogues (SPEC 9.5, 9.6).

Activation is where a draft stops being an idea and starts being something a
family can be shown, so every condition here fails closed and every refusal has
a stable machine name a reviewer can act on.

The content hash covers the reviewed content only: purpose, action text, claims,
citations, predicate, roles and corpus version. Lifecycle fields (status,
effective_from, the review identifiers themselves) are excluded on purpose,
because a reviewer approves a payload, not the state it later reaches; including
them would invalidate every review the moment the object was activated.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from packages.shared.domain.rag import (
    CatalogVersion,
    DocumentChunk,
    DocumentVersion,
    RecommendationSetVersion,
    ScenarioPredicate,
    StrategyVersion,
)
from packages.shared.enums import (
    AuthoringReviewKind,
    AuthoringReviewObjectType,
    CatalogStatus,
    StrategyStatus,
)
from rag.domain.citations import citations_are_verified, verify_strategy_citations
from rag.domain.documents import is_indexable
from rag.domain.hashing import CATALOG_ARTIFACT, SET_ARTIFACT, STRATEGY_ARTIFACT, seal
from rag.domain.reviews import ReviewLedger

_STRATEGY_LIFECYCLE: Final[frozenset[str]] = frozenset(
    {
        "status",
        "effective_from",
        "supersedes_version_id",
        "evidence_review_id",
        "clinical_review_id",
        "content_sha256",
    }
)
_SET_LIFECYCLE: Final[frozenset[str]] = frozenset(
    {"status", "effective_from", "suspended_at", "clinical_review_id", "content_sha256"}
)
_CATALOG_LIFECYCLE: Final[frozenset[str]] = frozenset(
    {"status", "effective_from", "suspended_at", "catalog_activation_review_id", "content_sha256"}
)


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    """Whether a version may be activated, and every reason it may not."""

    approved: bool
    blockers: tuple[str, ...] = ()

    @classmethod
    def of(cls, blockers: Iterable[str]) -> ActivationDecision:
        ordered = tuple(sorted(set(blockers)))
        return cls(approved=not ordered, blockers=ordered)


def predicate_payload(predicate: ScenarioPredicate) -> dict[str, Any]:
    """A predicate in a form whose hash does not depend on authoring order."""

    payload = predicate.canonical_payload()
    for key in ("required_field_values", "excluded_field_values"):
        payload[key] = {code: sorted(values) for code, values in sorted(payload[key].items())}
    for key in (
        "required_context_tags",
        "excluded_context_tags",
        "required_profile_tags",
        "contraindication_tags",
    ):
        payload[key] = sorted(payload[key])
    return payload


def strategy_content_payload(strategy: StrategyVersion) -> dict[str, Any]:
    """Exactly what an evidence and a clinical reviewer approve."""

    payload = {
        key: value
        for key, value in strategy.canonical_payload().items()
        if key not in _STRATEGY_LIFECYCLE
    }
    payload["allowed_executor_roles"] = sorted(payload["allowed_executor_roles"])
    payload["applicability_predicate"] = predicate_payload(strategy.applicability_predicate)
    return payload


def set_content_payload(version: RecommendationSetVersion) -> dict[str, Any]:
    """Predicate, order and reviewed priority: the three things a set decides."""

    payload = {
        key: value
        for key, value in version.canonical_payload().items()
        if key not in _SET_LIFECYCLE
    }
    payload["applicability_predicate"] = predicate_payload(version.applicability_predicate)
    return payload


def catalog_content_payload(version: CatalogVersion) -> dict[str, Any]:
    """The tenant, the corpus and the exact sets a catalogue publishes."""

    payload = {
        key: value
        for key, value in version.canonical_payload().items()
        if key not in _CATALOG_LIFECYCLE
    }
    payload["recommendation_set_version_ids"] = sorted(payload["recommendation_set_version_ids"])
    return payload


def strategy_content_sha256(strategy: StrategyVersion) -> str:
    return seal(strategy_content_payload(strategy), STRATEGY_ARTIFACT)


def set_content_sha256(version: RecommendationSetVersion) -> str:
    return seal(set_content_payload(version), SET_ARTIFACT)


def catalog_content_sha256(version: CatalogVersion) -> str:
    return seal(catalog_content_payload(version), CATALOG_ARTIFACT)


def _approved_review_missing(
    ledger: ReviewLedger,
    *,
    review_id: UUID | None,
    object_type: AuthoringReviewObjectType,
    object_version_id: UUID,
    review_kind: AuthoringReviewKind,
    content_sha256: str,
) -> bool:
    """True when the named review is absent, or present but not usable."""

    if review_id is None:
        return True
    return (
        ledger.approved_review(
            review_id=review_id,
            object_type=object_type,
            object_version_id=object_version_id,
            review_kind=review_kind,
            content_sha256=content_sha256,
        )
        is None
    )


def suspended_by_dependency(
    strategy: StrategyVersion,
    *,
    chunks: Mapping[UUID, DocumentChunk],
    documents: Mapping[UUID, DocumentVersion],
) -> bool:
    """True when any cited fragment now belongs to a retired source (INV-28)."""

    for citation in strategy.citations:
        chunk = chunks.get(citation.document_chunk_id)
        if chunk is None:
            return True
        document = documents.get(chunk.document_version_id)
        if document is None or not is_indexable(document):
            return True
    return False


def strategy_activation_decision(
    strategy: StrategyVersion,
    *,
    chunks: Iterable[DocumentChunk],
    documents: Iterable[DocumentVersion],
    ledger: ReviewLedger,
) -> ActivationDecision:
    """SPEC 9.5 activation: cited, literal, hashed, and reviewed by two people."""

    blockers: list[str] = []
    chunks_by_id = {chunk.document_chunk_id: chunk for chunk in chunks}
    documents_by_id = {document.document_version_id: document for document in documents}

    if not strategy.claims or not strategy.citations:
        blockers.append("claims_or_citations_empty")
    cited_claims = {citation.claim_id for citation in strategy.citations}
    if any(claim.claim_id not in cited_claims for claim in strategy.claims):
        blockers.append("claim_without_citation")
    if not citations_are_verified(verify_strategy_citations(strategy, chunks_by_id.values())):
        blockers.append("citation_not_verified")
    if suspended_by_dependency(strategy, chunks=chunks_by_id, documents=documents_by_id):
        blockers.append("source_retired")

    expected = strategy_content_sha256(strategy)
    if strategy.content_sha256 != expected:
        blockers.append("content_hash_mismatch")
    if not ledger.is_clean:
        blockers.append("review_ledger_conflict")

    evidence = clinical = None
    if strategy.evidence_review_id is None:
        blockers.append("evidence_review_missing")
    else:
        evidence = ledger.approved_review(
            review_id=strategy.evidence_review_id,
            object_type=AuthoringReviewObjectType.STRATEGY,
            object_version_id=strategy.strategy_version_id,
            review_kind=AuthoringReviewKind.EVIDENCE,
            content_sha256=expected,
        )
        if evidence is None:
            blockers.append("evidence_review_missing")

    if strategy.clinical_review_id is None:
        blockers.append("clinical_review_unavailable")
    else:
        clinical = ledger.approved_review(
            review_id=strategy.clinical_review_id,
            object_type=AuthoringReviewObjectType.STRATEGY,
            object_version_id=strategy.strategy_version_id,
            review_kind=AuthoringReviewKind.CLINICAL,
            content_sha256=expected,
        )
        if clinical is None:
            blockers.append("clinical_review_unavailable")

    # C31: two reviews, two people. Implementing or testing the system never
    # turns one person into both of them.
    if evidence is not None and clinical is not None and evidence.actor_id == clinical.actor_id:
        blockers.append("reviewers_not_distinct")

    return ActivationDecision.of(blockers)


def set_activation_decision(
    version: RecommendationSetVersion,
    *,
    strategies: Mapping[UUID, StrategyVersion],
    ledger: ReviewLedger,
) -> ActivationDecision:
    """A set activates only if every strategy is active and its predicate implies."""

    blockers: list[str] = []
    expected = set_content_sha256(version)
    if version.content_sha256 != expected:
        blockers.append("content_hash_mismatch")
    if not ledger.is_clean:
        blockers.append("review_ledger_conflict")

    if _approved_review_missing(
        ledger,
        review_id=version.clinical_review_id,
        object_type=AuthoringReviewObjectType.RECOMMENDATION_SET,
        object_version_id=version.recommendation_set_id,
        review_kind=AuthoringReviewKind.CLINICAL,
        content_sha256=expected,
    ):
        blockers.append("clinical_review_unavailable")

    for strategy_version_id in version.ordered_strategy_version_ids:
        strategy = strategies.get(strategy_version_id)
        if strategy is None:
            blockers.append("strategy_unknown")
            continue
        if strategy.status is not StrategyStatus.ACTIVE:
            blockers.append("strategy_not_active")
            continue
        # SPEC 9.6: the set predicate must imply each strategy predicate, so a
        # scenario that reaches the set cannot fail the strategy it contains.
        if not version.applicability_predicate.implies(strategy.applicability_predicate):
            blockers.append("predicate_not_implied")

    return ActivationDecision.of(blockers)


def catalog_review_subject(catalog: CatalogVersion) -> UUID:
    """The object a catalogue activation review points at.

    `CatalogVersion` is keyed by a version label rather than a UUID, so the
    review names the tenant whose single active catalogue is being decided.
    """

    return catalog.tenant_id


def catalog_activation_decision(
    catalog: CatalogVersion,
    *,
    sets: Mapping[UUID, RecommendationSetVersion],
    ledger: ReviewLedger,
) -> ActivationDecision:
    """A catalogue activates only if every set is active and it was approved."""

    blockers: list[str] = []
    expected = catalog_content_sha256(catalog)
    if catalog.content_sha256 != expected:
        blockers.append("content_hash_mismatch")
    if not ledger.is_clean:
        blockers.append("review_ledger_conflict")

    if _approved_review_missing(
        ledger,
        review_id=catalog.catalog_activation_review_id,
        object_type=AuthoringReviewObjectType.CATALOG,
        object_version_id=catalog_review_subject(catalog),
        review_kind=AuthoringReviewKind.CATALOG_ACTIVATION,
        content_sha256=expected,
    ):
        blockers.append("catalog_activation_review_missing")

    for set_version_id in catalog.recommendation_set_version_ids:
        version = sets.get(set_version_id)
        if version is None:
            blockers.append("set_unknown")
        elif version.status is not CatalogStatus.ACTIVE:
            blockers.append("set_not_active")

    return ActivationDecision.of(blockers)
