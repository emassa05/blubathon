"""Stable audit-day assignment (SPEC 6.8).

Ten percent of sessions show no suggestions, so the team can compare answers
given with and without help. The assignment has to be stable across reloads,
unpredictable from the client, and never recomputed for a past day; an HMAC over
tenant, subject, local date and policy version gives all three.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from ml.spec_constants import AUDIT_BUCKET_MODULUS, AUDIT_BUCKET_THRESHOLD
from packages.shared.canonical import canonical_date, stable_bucket


@dataclass(frozen=True, slots=True)
class AuditAssignment:
    """The bucket and the decision, so an auditor can reproduce both."""

    bucket: int
    audit_mode: bool
    modulus: int
    threshold: int


def assign_audit_mode(
    *,
    secret: bytes,
    tenant_id: UUID,
    subject_id: UUID,
    local_date: date,
    policy_version: str,
    modulus: int = AUDIT_BUCKET_MODULUS,
    threshold: int = AUDIT_BUCKET_THRESHOLD,
) -> AuditAssignment:
    """`bucket = HMAC(secret, tenant|subject|date|policy) mod 1000`, audited below 100.

    Persisted when the session opens. Reopening the session reads the stored
    value; calling this again with the same inputs returns the same answer, and
    a later policy version starts a different assignment rather than rewriting
    the old one.
    """

    bucket = stable_bucket(
        secret,
        [str(tenant_id), str(subject_id), canonical_date(local_date), policy_version],
        modulus,
    )
    return AuditAssignment(
        bucket=bucket,
        audit_mode=bucket < threshold,
        modulus=modulus,
        threshold=threshold,
    )
