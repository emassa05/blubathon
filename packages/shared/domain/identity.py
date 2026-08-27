"""Consent, accreditation, grants and the stable subject profile (SPEC 13.1).

Tenant and role never authorise on their own. A clinical operation needs an
active `SubjectAccessGrant` with the right capability, a professional needs a
versioned accreditation, and a secondary use needs its own consent purpose. None
of these substitute for one another.

All four contracts are append-only and are read through `project_as_of`, so
"active" is always evaluated at a cutoff, never as a mutable flag.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.domain.base import (
    AppendOnlyModel,
    BlubathonModel,
    NamespacedTag,
    Tag,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    AccreditationCapability,
    AuthoringBasisType,
    AuthoringScope,
    AuthorizationStatus,
    CohortKind,
    ConsentPurpose,
    DeploymentMode,
    GrantCapability,
    Role,
)


class _TimeBoundAuthorization(AppendOnlyModel):
    """Shared validity window and revocation semantics."""

    valid_from: UtcDatetime
    valid_until: UtcDatetime | None = None
    revoked_at: UtcDatetime | None = None
    status: AuthorizationStatus

    @model_validator(mode="after")
    def _window_is_ordered(self) -> _TimeBoundAuthorization:
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be strictly after valid_from")
        return self

    def is_active_at(self, cutoff: datetime) -> bool:
        """SPEC 13.1: active leaf, in window, and not revoked before the cutoff."""

        if self.status is not AuthorizationStatus.ACTIVE:
            return False
        if cutoff < self.valid_from:
            return False
        if self.valid_until is not None and cutoff >= self.valid_until:
            return False
        return not (self.revoked_at is not None and self.revoked_at <= cutoff)


class Consent(_TimeBoundAuthorization):
    """One purpose, one consent. Purposes are never reused across each other."""

    consent_id: UUID
    subject_id: UUID
    grantor_actor_id: UUID
    purpose: ConsentPurpose
    policy_version: VersionLabel
    granted_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.consent_id

    @property
    def record_kind(self) -> str:
        return "consent"

    @property
    def effective_instant(self) -> datetime | None:
        return self.granted_at

    def covers(self, purpose: ConsentPurpose, cutoff: datetime) -> bool:
        return self.purpose is purpose and self.is_active_at(cutoff)


class ProfessionalAccreditation(_TimeBoundAuthorization):
    """Organisational accreditation. Implementing the system never grants it."""

    accreditation_id: UUID
    actor_id: UUID
    capabilities: frozenset[AccreditationCapability]
    credential_policy_version: VersionLabel
    issuer_actor_id: UUID

    @property
    def record_id(self) -> UUID:
        return self.accreditation_id

    @property
    def record_kind(self) -> str:
        return "professional_accreditation"

    def grants(self, capability: AccreditationCapability, cutoff: datetime) -> bool:
        return capability in self.capabilities and self.is_active_at(cutoff)


class SubjectAccessGrant(_TimeBoundAuthorization):
    """Per-subject authorisation. Belonging to a tenant grants nothing."""

    subject_access_grant_id: UUID
    subject_id: UUID
    actor_id: UUID
    capabilities: frozenset[GrantCapability]
    issuer_actor_id: UUID

    @property
    def record_id(self) -> UUID:
        return self.subject_access_grant_id

    @property
    def record_kind(self) -> str:
        return "subject_access_grant"

    def grants(self, capability: GrantCapability, cutoff: datetime) -> bool:
        return capability in self.capabilities and self.is_active_at(cutoff)


class AuthoringUseAuthorization(_TimeBoundAuthorization):
    """Exporting a scenario to authoring needs its own basis; a grant is not one."""

    authorization_id: UUID
    subject_id: UUID
    authoring_request_id: UUID
    basis_type: AuthoringBasisType
    consent_id: UUID | None = None
    legal_basis_version: VersionLabel | None = None
    scope: AuthoringScope = AuthoringScope.GENERALIZE_QUERY_ONLY
    approved_by_privacy_reviewer: UUID
    approved_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.authorization_id

    @property
    def record_kind(self) -> str:
        return "authoring_use_authorization"

    @property
    def effective_instant(self) -> datetime | None:
        return self.approved_at

    @model_validator(mode="after")
    def _basis_matches_its_reference(self) -> AuthoringUseAuthorization:
        if self.basis_type is AuthoringBasisType.CONSENT:
            if self.consent_id is None:
                raise ValueError("a consent basis needs consent_id")
            if self.legal_basis_version is not None:
                raise ValueError("a consent basis must not carry legal_basis_version")
        else:
            if self.legal_basis_version is None:
                raise ValueError("an institutional basis needs legal_basis_version")
            if self.consent_id is not None:
                raise ValueError("an institutional basis must not carry consent_id")
        return self


class SubjectProfile(AppendOnlyModel):
    """Only the attributes matching needs, from closed catalogues (SPEC 5.7).

    Tags are never inferred from free notes, and `care_mode` is a token from a
    tenant-versioned catalogue that SPEC v0.3.0 does not enumerate.
    """

    subject_profile_id: UUID
    subject_id: UUID
    sensory_profile_tags: frozenset[Tag] = frozenset()
    communication_support_tags: frozenset[Tag] = frozenset()
    contraindication_tags: frozenset[Tag] = frozenset()
    care_mode: Tag
    profile_version: VersionLabel
    effective_from: UtcDatetime
    recorded_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.subject_profile_id

    @property
    def record_kind(self) -> str:
        return "subject_profile"

    @property
    def effective_instant(self) -> datetime | None:
        return self.effective_from

    def namespaced_profile_tags(self) -> tuple[NamespacedTag, ...]:
        """Sensory and communication tags, namespaced for a scenario (SPEC 9.7)."""

        tags = [f"sensory:{tag}" for tag in self.sensory_profile_tags]
        tags += [f"communication:{tag}" for tag in self.communication_support_tags]
        return tuple(sorted(tags))


class Subject(BlubathonModel):
    """Cohort membership decides which tracks may ever see this subject."""

    subject_id: UUID
    tenant_id: UUID
    cohort_kind: CohortKind


class AuthorizationContext(BlubathonModel):
    """The authorisation a service resolved before calling any domain code.

    Carried explicitly so a pure function can state what it required, instead of
    a route deciding and a formula assuming.
    """

    tenant_id: UUID
    actor_id: UUID
    roles: frozenset[Role]
    accreditation_capabilities: frozenset[AccreditationCapability] = frozenset()
    grant_capabilities: frozenset[GrantCapability] = frozenset()
    subject_id: UUID | None = None
    deployment_mode: DeploymentMode
    evaluated_at: UtcDatetime

    def has_role(self, role: Role) -> bool:
        return role in self.roles

    def may(self, capability: GrantCapability) -> bool:
        return capability in self.grant_capabilities

    def is_accredited_for(self, capability: AccreditationCapability) -> bool:
        return capability in self.accreditation_capabilities


class OperationRequirement(BlubathonModel):
    """One row of the SPEC 13.1 minimum operation matrix."""

    operation: str
    allowed_roles: frozenset[Role]
    grant_capability: GrantCapability
    accreditation_capability: AccreditationCapability | None = None
    note: str | None = None


_CARE_ROLES = frozenset({Role.CAREGIVER, Role.PROFESSIONAL})

OPERATION_MATRIX: tuple[OperationRequirement, ...] = (
    OperationRequirement(
        operation="read_subject_or_form",
        allowed_roles=_CARE_ROLES,
        grant_capability=GrantCapability.SUBJECT_READ,
        accreditation_capability=AccreditationCapability.SUBJECT_CARE,
    ),
    OperationRequirement(
        operation="write_daily_observation",
        allowed_roles=_CARE_ROLES,
        grant_capability=GrantCapability.DAILY_OBSERVATION_WRITE,
        accreditation_capability=AccreditationCapability.SUBJECT_CARE,
    ),
    OperationRequirement(
        operation="submit_form",
        allowed_roles=_CARE_ROLES,
        grant_capability=GrantCapability.FORM_SUBMIT,
        accreditation_capability=AccreditationCapability.SUBJECT_CARE,
    ),
    OperationRequirement(
        operation="report_outcome",
        allowed_roles=_CARE_ROLES,
        grant_capability=GrantCapability.OUTCOME_REPORT,
        note="the role must also appear in the target definition eligible_reporter_roles",
    ),
    OperationRequirement(
        operation="review_recommendation",
        allowed_roles=frozenset({Role.PROFESSIONAL}),
        grant_capability=GrantCapability.RECOMMENDATION_REVIEW,
        accreditation_capability=AccreditationCapability.SUBJECT_CARE,
        note="the actor must also satisfy the strategy required_approver_role",
    ),
    OperationRequirement(
        operation="record_execution",
        allowed_roles=_CARE_ROLES,
        grant_capability=GrantCapability.EXECUTION_RECORD,
        note="the role must appear in allowed_executor_roles of the referenced item",
    ),
    OperationRequirement(
        operation="read_clinical_evaluation",
        allowed_roles=frozenset({Role.MODEL_EVALUATOR, Role.PROFESSIONAL}),
        grant_capability=GrantCapability.EVALUATION_READ,
        accreditation_capability=AccreditationCapability.MODEL_EVALUATION,
    ),
)


class ConsentRevocationImpact(BlubathonModel):
    """What a revocation does to artifacts that already used the data.

    A snapshot stays immutable for audit, but it can no longer feed a new run
    (SPEC 13.2).
    """

    subject_id: UUID
    revoked_at: UtcDatetime
    purpose: ConsentPurpose
    blocks_new_runs: bool = True
    keeps_existing_snapshots_immutable: bool = True
    suspends_dependent_real_artifacts: bool = True
    affects_synthetic_artifacts: bool = False
    detail: dict[str, Any] = Field(default_factory=dict)
