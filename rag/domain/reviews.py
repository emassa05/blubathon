"""The authoring review ledger (SPEC 9.5).

An authoring review is not the professional review of a case. It is an
append-only event that says: this accredited person, holding this capability at
that instant, approved this exact payload hash.

A review identifier is therefore only usable when four things hold at once: the
projected leaf of the chain is the one being read, the accreditation granted the
capability the review kind requires at `reviewed_at`, the reviewed hash matches
the payload byte for byte, and the active decision is `approved`. Anything else
is not a review, it is a record of one.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from types import MappingProxyType
from typing import Final
from uuid import UUID

from packages.shared.domain.identity import ProfessionalAccreditation
from packages.shared.domain.rag import AuthoringReview
from packages.shared.enums import (
    AccreditationCapability,
    AuthoringReviewDecision,
    AuthoringReviewKind,
    AuthoringReviewObjectType,
)
from packages.shared.projection import project_as_of

_ReviewSubject = tuple[AuthoringReviewObjectType, AuthoringReviewKind]

# SPEC 13.1: target needs `target_review`, strategy and set `strategy_review`,
# evidence `evidence_review`, export `privacy_review`, catalogue activation
# `catalog_activation`. Capabilities are never substituted for one another.
REQUIRED_CAPABILITY: Final[MappingProxyType[_ReviewSubject, AccreditationCapability]] = (
    MappingProxyType(
        {
            (
                AuthoringReviewObjectType.TARGET_DEFINITION,
                AuthoringReviewKind.CLINICAL,
            ): AccreditationCapability.TARGET_REVIEW,
            (
                AuthoringReviewObjectType.STRATEGY,
                AuthoringReviewKind.CLINICAL,
            ): AccreditationCapability.STRATEGY_REVIEW,
            (
                AuthoringReviewObjectType.RECOMMENDATION_SET,
                AuthoringReviewKind.CLINICAL,
            ): AccreditationCapability.STRATEGY_REVIEW,
            (
                AuthoringReviewObjectType.DOCUMENT,
                AuthoringReviewKind.EVIDENCE,
            ): AccreditationCapability.EVIDENCE_REVIEW,
            (
                AuthoringReviewObjectType.STRATEGY,
                AuthoringReviewKind.EVIDENCE,
            ): AccreditationCapability.EVIDENCE_REVIEW,
            (
                AuthoringReviewObjectType.STRATEGY,
                AuthoringReviewKind.PRIVACY,
            ): AccreditationCapability.PRIVACY_REVIEW,
            (
                AuthoringReviewObjectType.DOCUMENT,
                AuthoringReviewKind.PRIVACY,
            ): AccreditationCapability.PRIVACY_REVIEW,
            (
                AuthoringReviewObjectType.CATALOG,
                AuthoringReviewKind.CATALOG_ACTIVATION,
            ): AccreditationCapability.CATALOG_ACTIVATION,
        }
    )
)


def required_capability(
    object_type: AuthoringReviewObjectType, review_kind: AuthoringReviewKind
) -> AccreditationCapability | None:
    """The one capability this review kind needs, or `None` for an unknown pair."""

    return REQUIRED_CAPABILITY.get((object_type, review_kind))


class ReviewLedger:
    """Append-only authoring reviews, read at a cutoff against accreditations."""

    def __init__(
        self,
        reviews: Iterable[AuthoringReview],
        accreditations: Iterable[ProfessionalAccreditation],
        *,
        cutoff: datetime,
    ) -> None:
        self._cutoff = cutoff
        projection = project_as_of(tuple(reviews), cutoff)
        self._conflicts = projection.conflicts
        self._reviews = projection.leaves
        self._accreditations = tuple(accreditations)

    @property
    def is_clean(self) -> bool:
        """False when a correction chain branched, cycled or crossed tenants."""

        return not self._conflicts

    def _accredited(self, review: AuthoringReview) -> bool:
        capability = required_capability(review.object_type, review.review_kind)
        if capability is None:
            return False
        return any(
            accreditation.accreditation_id == review.accreditation_id
            and accreditation.actor_id == review.actor_id
            and accreditation.tenant_id == review.tenant_id
            and accreditation.grants(capability, review.reviewed_at)
            for accreditation in self._accreditations
        )

    def approved_review(
        self,
        *,
        review_id: UUID,
        object_type: AuthoringReviewObjectType,
        object_version_id: UUID,
        review_kind: AuthoringReviewKind,
        content_sha256: str,
    ) -> AuthoringReview | None:
        """The named review, only if it is usable in every sense at the cutoff."""

        for review in self._reviews:
            if review.authoring_review_id != review_id:
                continue
            if review.object_type is not object_type or review.review_kind is not review_kind:
                return None
            if review.object_version_id != object_version_id:
                return None
            if review.decision is not AuthoringReviewDecision.APPROVED:
                return None
            if review.reviewed_content_sha256 != content_sha256:
                return None
            if review.reviewed_at > self._cutoff:
                return None
            if not self._accredited(review):
                return None
            return review
        return None
