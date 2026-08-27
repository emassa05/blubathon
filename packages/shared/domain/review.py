"""Recommendation instances, professional review, human plans and execution.

Three different facts, three different rows (SPEC 10.4). A professional's
preference is a `RecommendationReview`, exposure to a strategy is a
`StrategyExecution`, and what happened afterwards is an `OutcomeReport`.
Approved plus no event is not evidence of efficacy.

`review_status` is never stored on the instance: the absence of an active review
means pending, and storing it would create a second source of truth (SPEC 10.1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.constants import MAX_RUNTIME_STRATEGIES
from packages.shared.domain.base import (
    AppendOnlyModel,
    FaroModel,
    Sha256Hex,
    SpanishText,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    ExecutionStatus,
    NonActionableReason,
    RecommendationAbstentionReason,
    ReviewDecision,
    Role,
    RuntimeStatus,
)


class RecommendationInstance(FaroModel):
    """Written once, when the episode is created. Later GETs only read it."""

    recommendation_instance_id: UUID
    tenant_id: UUID
    subject_id: UUID
    prediction_episode_id: UUID
    scenario_hash: str = Field(min_length=1)
    catalog_version: VersionLabel | None = None
    corpus_version: VersionLabel | None = None
    strategy_version_ids: tuple[UUID, ...] = ()
    runtime_status: RuntimeStatus
    abstention_reasons: tuple[RecommendationAbstentionReason, ...] = ()
    non_actionable: NonActionableReason | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _instance_matches_its_runtime_decision(self) -> Self:
        if self.runtime_status is RuntimeStatus.MATCHED:
            if not self.strategy_version_ids:
                raise ValueError("a matched instance persists the strategies it served")
            if len(self.strategy_version_ids) > MAX_RUNTIME_STRATEGIES:
                raise ValueError(f"at most {MAX_RUNTIME_STRATEGIES} strategies per instance")
            if self.abstention_reasons:
                raise ValueError("a matched instance has no abstention reasons")
            if self.catalog_version is None or self.corpus_version is None:
                raise ValueError("a matched instance names the exact versions it served")
        else:
            if self.strategy_version_ids:
                raise ValueError("an abstained instance persists no strategies")
            if not self.abstention_reasons:
                raise ValueError("an abstained instance keeps its reason")
        return self


class HumanPlanVersion(AppendOnlyModel):
    """A professional's substitution. It never inherits the RAG citations."""

    human_plan_version_id: UUID
    recommendation_instance_id: UUID
    substituted_strategy_version_id: UUID
    action_text_es: SpanishText
    author_actor_id: UUID
    authored_at: UtcDatetime
    plan_version: VersionLabel
    allowed_executor_roles: frozenset[Role]
    content_sha256: Sha256Hex

    @property
    def record_id(self) -> UUID:
        return self.human_plan_version_id

    @property
    def record_kind(self) -> str:
        return "human_plan_version"

    @property
    def effective_instant(self) -> datetime | None:
        return self.authored_at

    @model_validator(mode="after")
    def _roles_are_declared(self) -> Self:
        if not self.allowed_executor_roles:
            raise ValueError("a human plan names at least one allowed executor role")
        return self

    def roles_are_subset_of(self, strategy_roles: frozenset[Role]) -> bool:
        """A substitution may only narrow who is allowed to apply it (SPEC 10.2)."""

        return self.allowed_executor_roles <= strategy_roles


class RecommendationReview(AppendOnlyModel):
    """One decision about exactly one strategy version, never a whole set."""

    review_id: UUID
    recommendation_instance_id: UUID
    strategy_version_id: UUID
    decision: ReviewDecision
    reviewed_by: UUID
    reviewer_role: Role
    reviewed_at: UtcDatetime
    human_plan_version_id: UUID | None = None

    @property
    def record_id(self) -> UUID:
        return self.review_id

    @property
    def record_kind(self) -> str:
        return "recommendation_review"

    @property
    def effective_instant(self) -> datetime | None:
        return self.reviewed_at

    @model_validator(mode="after")
    def _substitution_carries_its_plan(self) -> Self:
        if self.decision is ReviewDecision.HUMAN_PLAN_SUBSTITUTED:
            if self.human_plan_version_id is None:
                raise ValueError("a substitution references the human plan it created")
        elif self.human_plan_version_id is not None:
            raise ValueError("only a substitution references a human plan")
        return self

    @property
    def is_favourable(self) -> bool:
        """The two decisions that require the strategy's approver role."""

        return self.decision in {
            ReviewDecision.APPROVED,
            ReviewDecision.HUMAN_PLAN_SUBSTITUTED,
        }


class StrategyExecution(AppendOnlyModel):
    """Whether it was applied, recorded separately from whether it was approved."""

    strategy_execution_id: UUID
    recommendation_instance_id: UUID
    strategy_version_id: UUID | None = None
    human_plan_version_id: UUID | None = None
    status: ExecutionStatus
    actor_id: UUID
    actor_role: Role
    recorded_at: UtcDatetime
    applied_at: UtcDatetime | None = None

    @property
    def record_id(self) -> UUID:
        return self.strategy_execution_id

    @property
    def record_kind(self) -> str:
        return "strategy_execution"

    @property
    def effective_instant(self) -> datetime | None:
        return self.recorded_at

    @model_validator(mode="after")
    def _references_exactly_one_item(self) -> Self:
        referenced = [self.strategy_version_id, self.human_plan_version_id]
        if sum(value is not None for value in referenced) != 1:
            raise ValueError("an execution references a strategy or a human plan, never both")

        if self.status is ExecutionStatus.APPLIED:
            if self.applied_at is None:
                raise ValueError("an applied execution records when it was applied")
            if self.applied_at > self.recorded_at:
                raise ValueError("applied_at may be retrospective but never in the future")
        elif self.applied_at is not None:
            raise ValueError("only an applied execution carries applied_at")
        return self


def exposure_is_eligible(
    *,
    instance_created_at: datetime,
    review: RecommendationReview,
    execution: StrategyExecution,
    target_end_at: datetime,
    outcome_occurred_at: datetime | None,
) -> bool:
    """The SPEC 10.3 chronology for attributing an exposure to a window.

    A late or retrospectively reported application is kept as history but is not
    attributed to the outcome of that window.
    """

    if execution.status is not ExecutionStatus.APPLIED or execution.applied_at is None:
        return False
    if not instance_created_at <= review.reviewed_at <= execution.applied_at:
        return False
    if execution.applied_at > target_end_at:
        return False
    if outcome_occurred_at is not None and execution.applied_at >= outcome_occurred_at:
        return False
    if execution.strategy_version_id is not None:
        return review.decision is ReviewDecision.APPROVED
    return review.decision is ReviewDecision.HUMAN_PLAN_SUBSTITUTED
