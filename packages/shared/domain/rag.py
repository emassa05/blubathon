"""Corpus, strategies, catalogues and the minimal matching scenario (SPEC 9).

The RAG works at authoring time, not per clinical query. Everything the runtime
serves has already been retrieved, cited, verified and reviewed twice, and the
runtime only matches a categorical scenario against precomputed sets.

`ScenarioV1` has exactly one representation and `ScenarioPredicate` exactly one
form. Matching is fail-closed: an unknown field, tag or version does not match,
it refuses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import AnyUrl, Field, model_validator

from packages.shared.constants import SCENARIO_SCHEMA_VERSION
from packages.shared.domain.base import (
    AppendOnlyModel,
    BlubathonModel,
    NamespacedTag,
    Sha256Hex,
    SpanishText,
    Tag,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    AuthoringRequestStatus,
    AuthoringReviewDecision,
    AuthoringReviewKind,
    AuthoringReviewObjectType,
    CatalogStatus,
    DocumentStatus,
    FieldCode,
    RecommendationAbstentionReason,
    RetrievalMode,
    Role,
    RuntimeStatus,
    Source,
    StrategyStatus,
)
from packages.shared.field_catalog import (
    FIELD_CATALOG,
    SCENARIO_ALLOWLIST_V1,
    validate_field_value,
)


def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


class DocumentVersion(BlubathonModel):
    """Without version, rights and hashes a document is not indexed (SPEC 9.2)."""

    document_version_id: UUID
    source_id: UUID
    publisher: str
    title: str
    document_version: VersionLabel
    publication_date: str
    retrieved_at: UtcDatetime
    canonical_url: AnyUrl
    rights_basis: str
    original_bytes_sha256: Sha256Hex
    extracted_text_sha256: Sha256Hex
    extraction_manifest_id: UUID
    language: str
    status: DocumentStatus

    @model_validator(mode="after")
    def _rights_are_declared(self) -> Self:
        if not self.rights_basis.strip() or self.rights_basis == "undeclared":
            raise ValueError("a document without a declared rights basis is not indexable")
        return self


class DocumentChunk(BlubathonModel):
    """A citation without a verifiable locator cannot be published (SPEC 9.3)."""

    document_chunk_id: UUID
    document_version_id: UUID
    locator: str = Field(min_length=1)
    text: str = Field(min_length=1)
    chunk_sha256: Sha256Hex
    chunker_version: VersionLabel


class AuthoringBuildManifest(BlubathonModel):
    """Everything that could change a retrieval result, fixed and hashed.

    `lexical_only` is a declared mode, not a silent degradation: no model is ever
    downloaded to make a hybrid build succeed (SPEC 9.4).
    """

    authoring_build_manifest_id: UUID
    retrieval_mode: RetrievalMode
    extractor_version: VersionLabel
    ocr_version: VersionLabel | None = None
    normalization_version: VersionLabel
    chunker_version: VersionLabel
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    tokenizer_version: VersionLabel
    bm25_parameters: dict[str, float]
    lexical_top_k: int = Field(gt=0)
    dense_model_id: str | None = None
    dense_model_sha256: Sha256Hex | None = None
    dense_top_k: int | None = None
    rrf_k: int | None = None
    final_chunk_count: int = Field(gt=0)
    prompt_version: VersionLabel | None = None
    library_versions: dict[str, str]
    platform: str
    built_at: UtcDatetime
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _mode_matches_its_parameters(self) -> Self:
        dense = (self.dense_model_id, self.dense_model_sha256, self.dense_top_k, self.rrf_k)
        if self.retrieval_mode is RetrievalMode.HYBRID:
            if any(value is None for value in dense):
                raise ValueError("a hybrid build records its dense model, top k and RRF k")
        elif any(value is not None for value in dense):
            raise ValueError("a lexical_only build carries no dense retrieval parameters")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk overlap must be smaller than chunk size")
        return self


class CorpusVersion(BlubathonModel):
    """The exact set of document versions a catalogue was built from."""

    corpus_version: VersionLabel
    document_version_ids: tuple[UUID, ...] = Field(min_length=1)
    authoring_build_manifest_id: UUID
    created_at: UtcDatetime
    content_sha256: Sha256Hex


class AuthoringReview(AppendOnlyModel):
    """Authoring review is a different entity from a case review (SPEC 9.5)."""

    authoring_review_id: UUID
    object_type: AuthoringReviewObjectType
    object_version_id: UUID
    review_kind: AuthoringReviewKind
    actor_id: UUID
    accreditation_id: UUID
    decision: AuthoringReviewDecision
    reviewed_content_sha256: Sha256Hex
    reviewed_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.authoring_review_id

    @property
    def record_kind(self) -> str:
        return "authoring_review"

    @property
    def effective_instant(self) -> datetime | None:
        return self.reviewed_at


class StrategyCitation(BlubathonModel):
    """Links one claim to one literal fragment of one hashed chunk."""

    citation_id: UUID
    claim_id: UUID
    document_chunk_id: UUID
    locator: str = Field(min_length=1)
    quoted_text: str = Field(min_length=1)
    chunk_sha256: Sha256Hex
    canonical_url: AnyUrl


class StrategyClaim(BlubathonModel):
    """A claim is a span of the reviewed action text, with its own citations."""

    claim_id: UUID
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    claim_text_es: SpanishText
    citation_ids: tuple[UUID, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _span_is_ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("a claim span ends after it starts")
        return self


class StrategyVersion(BlubathonModel):
    """Runtime serves `action_text_es` verbatim; it never recomposes text."""

    strategy_id: UUID
    strategy_version_id: UUID
    purpose_es: SpanishText
    action_text_es: SpanishText
    claims: tuple[StrategyClaim, ...] = Field(min_length=1)
    citations: tuple[StrategyCitation, ...] = Field(min_length=1)
    applicability_predicate: ScenarioPredicate
    required_approver_role: Role
    allowed_executor_roles: frozenset[Role]
    corpus_version: VersionLabel
    evidence_review_id: UUID | None = None
    clinical_review_id: UUID | None = None
    effective_from: UtcDatetime
    supersedes_version_id: UUID | None = None
    status: StrategyStatus
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _claims_are_cited_and_anchored(self) -> Self:
        citation_ids = {citation.citation_id for citation in self.citations}
        by_claim: dict[UUID, list[StrategyCitation]] = {}
        for citation in self.citations:
            by_claim.setdefault(citation.claim_id, []).append(citation)

        for claim in self.claims:
            if claim.end > len(self.action_text_es):
                raise ValueError("a claim span falls outside the action text")
            if self.action_text_es[claim.start : claim.end] != claim.claim_text_es:
                raise ValueError("claim_text_es must match action_text_es at its offsets")
            missing = set(claim.citation_ids) - citation_ids
            if missing:
                raise ValueError("a claim references a citation the strategy does not carry")
            if not by_claim.get(claim.claim_id):
                raise ValueError("every claim needs at least one verifiable citation")

        if not self.allowed_executor_roles:
            raise ValueError("a strategy names at least one allowed executor role")

        if self.status is StrategyStatus.ACTIVE:
            if self.evidence_review_id is None or self.clinical_review_id is None:
                raise ValueError("activation requires both an evidence and a clinical review")
            if self.evidence_review_id == self.clinical_review_id:
                raise ValueError("one person cannot perform both reviews")
        return self


class ScenarioV1(BlubathonModel):
    """The minimal matching payload. No identity, notes, external IDs or history.

    Treated as potentially pseudonymised while a combination of attributes could
    be linkable; it is never presumed anonymous (SPEC 9.7).
    """

    schema_version: str = SCENARIO_SCHEMA_VERSION
    field_values: dict[FieldCode, str] = Field(default_factory=dict)
    context_tags: tuple[Tag, ...] = ()
    profile_tags: tuple[NamespacedTag, ...] = ()
    contraindication_tags: tuple[Tag, ...] = ()

    @model_validator(mode="after")
    def _values_are_allowlisted_and_tags_canonical(self) -> Self:
        if self.schema_version != SCENARIO_SCHEMA_VERSION:
            raise ValueError(f"scenario schema must be {SCENARIO_SCHEMA_VERSION}")
        for code, value in self.field_values.items():
            if code not in SCENARIO_ALLOWLIST_V1:
                raise ValueError(f"{code} is outside the scenario allowlist v1")
            validate_field_value(code, value)
        object.__setattr__(self, "context_tags", _sorted_unique(self.context_tags))
        object.__setattr__(self, "profile_tags", _sorted_unique(self.profile_tags))
        object.__setattr__(
            self, "contraindication_tags", _sorted_unique(self.contraindication_tags)
        )
        return self

    def canonical_payload(self) -> dict[str, Any]:
        """Deduplicated, sorted and key-ordered before JCS (SPEC 9.7)."""

        return {
            "schema_version": self.schema_version,
            "field_values": {
                str(code): self.field_values[code] for code in sorted(self.field_values, key=str)
            },
            "context_tags": list(self.context_tags),
            "profile_tags": list(self.profile_tags),
            "contraindication_tags": list(self.contraindication_tags),
        }


class ScenarioPredicate(BlubathonModel):
    """Fail-closed applicability. Used unchanged by sets and strategies."""

    required_field_values: dict[FieldCode, tuple[str, ...]] = Field(default_factory=dict)
    excluded_field_values: dict[FieldCode, tuple[str, ...]] = Field(default_factory=dict)
    required_context_tags: tuple[Tag, ...] = ()
    excluded_context_tags: tuple[Tag, ...] = ()
    required_profile_tags: tuple[NamespacedTag, ...] = ()
    contraindication_tags: tuple[Tag, ...] = ()

    @model_validator(mode="after")
    def _values_are_known(self) -> Self:
        for mapping in (self.required_field_values, self.excluded_field_values):
            for code, values in mapping.items():
                if code not in FIELD_CATALOG:
                    raise ValueError(f"{code} is not a known field")
                if not values:
                    raise ValueError(f"{code} lists no values, which can never match")
                for value in values:
                    validate_field_value(code, value)
        object.__setattr__(
            self, "required_context_tags", _sorted_unique(self.required_context_tags)
        )
        object.__setattr__(
            self, "excluded_context_tags", _sorted_unique(self.excluded_context_tags)
        )
        object.__setattr__(
            self, "required_profile_tags", _sorted_unique(self.required_profile_tags)
        )
        object.__setattr__(
            self, "contraindication_tags", _sorted_unique(self.contraindication_tags)
        )
        return self

    def matches(self, scenario: ScenarioV1) -> bool:
        """Every required value present, no excluded value, tags disjoint as declared."""

        for code, allowed in self.required_field_values.items():
            value = scenario.field_values.get(code)
            if value is None or value not in allowed:
                return False
        for code, forbidden in self.excluded_field_values.items():
            value = scenario.field_values.get(code)
            if value is not None and value in forbidden:
                return False

        context = set(scenario.context_tags)
        profile = set(scenario.profile_tags)
        contraindications = set(scenario.contraindication_tags)
        if not set(self.required_context_tags) <= context:
            return False
        if set(self.excluded_context_tags) & context:
            return False
        if not set(self.required_profile_tags) <= profile:
            return False
        return not set(self.contraindication_tags) & contraindications

    def implies(self, other: ScenarioPredicate) -> bool:
        """Conservative implication check used when activating a set (SPEC 9.6).

        Sound but not complete: it may refuse an implication that in fact holds,
        which fails closed. It never accepts one that does not.
        """

        for code, required in other.required_field_values.items():
            mine = self.required_field_values.get(code)
            if mine is None or not set(mine) <= set(required):
                return False
        for code, forbidden in other.excluded_field_values.items():
            mine_excluded = set(self.excluded_field_values.get(code, ()))
            if set(forbidden) <= mine_excluded:
                continue
            mine_required = self.required_field_values.get(code)
            if mine_required is None or set(mine_required) & set(forbidden):
                return False
        if not set(other.required_context_tags) <= set(self.required_context_tags):
            return False
        if not set(other.excluded_context_tags) <= set(self.excluded_context_tags):
            return False
        if not set(other.required_profile_tags) <= set(self.required_profile_tags):
            return False
        return set(other.contraindication_tags) <= set(self.contraindication_tags)


class RecommendationSetVersion(BlubathonModel):
    """An ordered, reviewed set of strategies with its own predicate."""

    recommendation_set_id: UUID
    recommendation_set_version: VersionLabel
    applicability_predicate: ScenarioPredicate
    ordered_strategy_version_ids: tuple[UUID, ...] = Field(min_length=1)
    reviewed_priority: int = Field(ge=0)
    clinical_review_id: UUID | None = None
    status: CatalogStatus
    effective_from: UtcDatetime
    suspended_at: UtcDatetime | None = None
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _activation_requires_review(self) -> Self:
        if self.status is CatalogStatus.ACTIVE and self.clinical_review_id is None:
            raise ValueError("activating a set requires an accredited clinical review")
        if len(set(self.ordered_strategy_version_ids)) != len(self.ordered_strategy_version_ids):
            raise ValueError("a set lists each strategy version once")
        return self


class CatalogVersion(BlubathonModel):
    """At most one active, effective catalogue per tenant at any instant."""

    catalog_version: VersionLabel
    tenant_id: UUID
    corpus_version: VersionLabel
    recommendation_set_version_ids: tuple[UUID, ...] = Field(min_length=1)
    catalog_activation_review_id: UUID | None = None
    status: CatalogStatus
    effective_from: UtcDatetime
    suspended_at: UtcDatetime | None = None
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def _activation_requires_its_review(self) -> Self:
        if self.status is CatalogStatus.ACTIVE and self.catalog_activation_review_id is None:
            raise ValueError("activating a catalogue requires an approved activation review")
        return self


class AuthoringRequestIntent(BlubathonModel):
    """What the pure runtime returns for an uncovered scenario. It writes nothing."""

    scenario_hash: str = Field(min_length=1)
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    reasons: tuple[RecommendationAbstentionReason, ...] = Field(min_length=1)


class AuthoringRequest(AppendOnlyModel):
    """Persisted intent. Its scenario payload stays encrypted inside the clinic."""

    authoring_request_id: UUID
    subject_id: UUID
    prediction_episode_id: UUID
    scenario_hash: str = Field(min_length=1)
    scenario_schema_version: str = SCENARIO_SCHEMA_VERSION
    encrypted_scenario_payload: str = Field(min_length=1)
    reasons: tuple[RecommendationAbstentionReason, ...] = Field(min_length=1)
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    status: AuthoringRequestStatus
    created_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.authoring_request_id

    @property
    def record_kind(self) -> str:
        return "authoring_request"

    @property
    def effective_instant(self) -> datetime | None:
        return self.created_at


class ScenarioBuildResult(BlubathonModel):
    """Outcome of the pure P1 `build_scenario` facade (SPEC 9.7).

    P2 persists this or the abstention; it never re-derives the precedence.
    """

    status: RuntimeStatus
    scenario: ScenarioV1 | None = None
    scenario_hash: str | None = None
    builder_version: VersionLabel
    source: Source | None = None
    profile_version: VersionLabel | None = None
    reasons: tuple[RecommendationAbstentionReason, ...] = ()

    @model_validator(mode="after")
    def _built_or_abstained(self) -> Self:
        if self.status is RuntimeStatus.MATCHED:
            if self.scenario is None or self.scenario_hash is None:
                raise ValueError("a built scenario carries the payload and its hash")
            if self.reasons:
                raise ValueError("a built scenario has no abstention reasons")
        else:
            if self.scenario is not None or self.scenario_hash is not None:
                raise ValueError("an abstained build carries no scenario")
            if not self.reasons:
                raise ValueError("an abstention states its reason")
        return self


class RuntimeStrategyMatch(BlubathonModel):
    """One matched strategy in runtime order, with the citations of its version."""

    strategy_version_id: UUID
    recommendation_set_id: UUID
    recommendation_set_version: VersionLabel
    reviewed_priority: int
    position_in_set: int = Field(ge=0)
    action_text_es: SpanishText
    citations: tuple[StrategyCitation, ...] = Field(min_length=1)


class RuntimeDecision(BlubathonModel):
    """The pure runtime answer: at most three strategies, or an abstention."""

    status: RuntimeStatus
    scenario_hash: str
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    matches: tuple[RuntimeStrategyMatch, ...] = ()
    reasons: tuple[RecommendationAbstentionReason, ...] = ()
    authoring_request_intent: AuthoringRequestIntent | None = None

    @model_validator(mode="after")
    def _matched_or_abstained(self) -> Self:
        from packages.shared.constants import MAX_RUNTIME_STRATEGIES

        if self.status is RuntimeStatus.MATCHED:
            if not self.matches:
                raise ValueError("a matched decision carries at least one strategy")
            if len(self.matches) > MAX_RUNTIME_STRATEGIES:
                raise ValueError(f"runtime returns at most {MAX_RUNTIME_STRATEGIES} strategies")
            if self.reasons or self.authoring_request_intent is not None:
                raise ValueError("a matched decision has no abstention reason or intent")
            if self.catalog_version is None or self.corpus_version is None:
                raise ValueError("a matched decision names the exact versions it served")
        else:
            if self.matches:
                raise ValueError("an abstained decision returns no strategies")
            if not self.reasons:
                raise ValueError("an abstention states exactly why")
            if self.authoring_request_intent is None:
                raise ValueError("an abstention returns an authoring request intent")
        return self


def resolve_catalog_readiness(
    *,
    corpus_available: bool,
    blocked_only_by_clinical_review: bool,
    dependency_suspended: bool,
    active_catalog_count: int,
) -> RecommendationAbstentionReason | None:
    """SPEC 9.6 precedence, in order. `None` means ready.

    `clinical_review_unavailable` never collapses into `catalog_not_ready`, and
    ambiguity or suspension fails closed.
    """

    if not corpus_available:
        return RecommendationAbstentionReason.CORPUS_NOT_READY
    if blocked_only_by_clinical_review:
        return RecommendationAbstentionReason.CLINICAL_REVIEW_UNAVAILABLE
    if dependency_suspended:
        return RecommendationAbstentionReason.CATALOG_SUSPENDED
    if active_catalog_count > 1:
        return RecommendationAbstentionReason.CATALOG_AMBIGUOUS
    if active_catalog_count == 0:
        return RecommendationAbstentionReason.CATALOG_NOT_READY
    return None


StrategyVersion.model_rebuild()
