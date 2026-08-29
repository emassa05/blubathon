"""Outcome requests, reports, resolutions and adjudications.

A report and a resolution are different types on purpose. A person answers
`yes`, `no` or `unknown`; the system resolves to `pending`, `yes`, `no`,
`unknown` or `conflicted`. The absence of a report is never a negative outcome,
and an explicit `unknown` resolves nothing.

The derivations live here so P2 does not reimplement them: request state is a
function of the active resolution and the clock, never a second state machine
that can drift out of sync.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.domain.base import (
    AppendOnlyModel,
    BlubathonModel,
    SpanishText,
    UtcDatetime,
    VersionLabel,
)
from packages.shared.enums import (
    DataOrigin,
    IntakeChannel,
    OutcomeReportValue,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    Role,
    TimingStatus,
)


class OutcomeRequest(BlubathonModel):
    """Immutable scheduling record. Its state is derived, never mutated."""

    outcome_request_id: UUID
    tenant_id: UUID
    subject_id: UUID
    prediction_episode_id: UUID
    target_definition_version: VersionLabel
    eligible_reporter_roles: frozenset[Role]
    target_start_at: UtcDatetime
    target_end_at: UtcDatetime
    capture_deadline_at: UtcDatetime
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _window_is_ordered(self) -> OutcomeRequest:
        if not self.target_start_at < self.target_end_at <= self.capture_deadline_at:
            raise ValueError("target window and capture deadline are out of order")
        if not self.eligible_reporter_roles:
            raise ValueError("an outcome request names at least one eligible reporter role")
        return self


class OutcomeReport(AppendOnlyModel):
    """One person's answer, kept forever even when it arrives too late."""

    outcome_report_id: UUID
    prediction_episode_id: UUID
    target_definition_version: VersionLabel
    reporter_actor_id: UUID
    reporter_role: Role
    value: OutcomeReportValue
    occurred_at: UtcDatetime | None = None
    reported_at: UtcDatetime
    timing_status: TimingStatus
    data_origin: DataOrigin
    intake_channel: IntakeChannel
    source_mapping_id: UUID | None = None

    @property
    def record_id(self) -> UUID:
        return self.outcome_report_id

    @property
    def record_kind(self) -> str:
        return "outcome_report"

    @property
    def effective_instant(self) -> datetime | None:
        return self.reported_at

    @model_validator(mode="after")
    def _value_and_channel_carry_what_they_need(self) -> OutcomeReport:
        if self.value is OutcomeReportValue.YES:
            if self.occurred_at is None:
                raise ValueError("a yes report states when the event occurred")
            if self.occurred_at > self.reported_at:
                raise ValueError("an event cannot occur after it was reported")
        elif self.occurred_at is not None:
            raise ValueError("only a yes report carries occurred_at")

        if self.timing_status is TimingStatus.MISSING:
            raise ValueError("missing describes an absent report, not a stored one")

        if self.intake_channel is IntakeChannel.IMPORT:
            if self.source_mapping_id is None:
                raise ValueError("an imported report names its approved source mapping")
        elif self.source_mapping_id is not None:
            raise ValueError("a form report carries no source mapping")
        return self


class OutcomeResolution(AppendOnlyModel):
    """An append-only materialisation recomputed after every correction."""

    outcome_resolution_id: UUID
    prediction_episode_id: UUID
    status: OutcomeResolutionStatus
    resolved_at: UtcDatetime | None = None
    qualifying_report_id: UUID | None = None
    ever_conflicted: bool
    resolution_version: int = Field(ge=1)

    @property
    def record_id(self) -> UUID:
        return self.outcome_resolution_id

    @property
    def record_kind(self) -> str:
        return "outcome_resolution"

    @model_validator(mode="after")
    def _status_carries_its_evidence(self) -> OutcomeResolution:
        conclusive = {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}
        if self.status in conclusive:
            if self.qualifying_report_id is None:
                raise ValueError("a conclusive resolution names its qualifying report")
            if self.resolved_at is None:
                raise ValueError("a conclusive resolution records when it resolved")
        else:
            if self.qualifying_report_id is not None:
                raise ValueError("only a conclusive resolution has a qualifying report")
            if self.status is OutcomeResolutionStatus.PENDING and self.resolved_at is not None:
                raise ValueError("a pending resolution has no resolved_at")

        if self.status is OutcomeResolutionStatus.CONFLICTED and not self.ever_conflicted:
            raise ValueError("a conflicted resolution is by definition ever_conflicted")
        return self

    @property
    def excluded_from_primary_dataset(self) -> bool:
        """Any episode that was ever conflicted stays out of the v0.3 dataset."""

        return self.ever_conflicted


class OutcomeAdjudication(AppendOnlyModel):
    """An operational decision on a conflict. It does not restore eligibility."""

    outcome_adjudication_id: UUID
    prediction_episode_id: UUID
    actor_id: UUID
    actor_role: Role
    decision: OutcomeReportValue
    reason_es: SpanishText
    decided_at: UtcDatetime

    @property
    def record_id(self) -> UUID:
        return self.outcome_adjudication_id

    @property
    def record_kind(self) -> str:
        return "outcome_adjudication"

    @property
    def effective_instant(self) -> datetime | None:
        return self.decided_at


class OutcomeWindow(NamedTuple):
    """The three instants that classify every report."""

    target_start_at: datetime
    target_end_at: datetime
    capture_deadline_at: datetime


def classify_timing(reported_at: datetime, window: OutcomeWindow) -> TimingStatus:
    """Boundaries, exactly: early is strict, on_time is inclusive both ways."""

    if reported_at < window.target_end_at:
        return TimingStatus.EARLY
    if reported_at <= window.capture_deadline_at:
        return TimingStatus.ON_TIME
    return TimingStatus.LATE


def report_is_eligible(report: OutcomeReport, window: OutcomeWindow) -> bool:
    """Eligibility rules 1 and 2 of the resolution algorithm.

    A `yes` may resolve early once the event has actually happened inside the
    window.

    A `no` may resolve early too. It did not use to: the argument was that an
    early `no` cannot know about the rest of the window, so it was recorded and
    left provisional until the window closed. That is true of the reading, but
    it was the wrong place to enforce it. The caregiver is the only source of
    this answer, and the interface has a button that asks for it; a report that
    is accepted, stored and then ignored gives back no signal at all — the
    request stays open, the card stays up and nothing says why. Between refusing
    the answer and taking it, taking it is the honest one, and `timing_status`
    still records that it came in early for anyone measuring later.

    A late report is still not eligible, either way: past the capture deadline
    the episode has already resolved and reopening it is a different decision.
    """

    if report.timing_status not in {TimingStatus.EARLY, TimingStatus.ON_TIME}:
        return False
    if report.value is OutcomeReportValue.YES:
        occurred = report.occurred_at
        return occurred is not None and window.target_start_at < occurred <= window.target_end_at
    return report.value is OutcomeReportValue.NO


class ResolutionOutcome(NamedTuple):
    """The derived resolution before it is persisted as a new version."""

    status: OutcomeResolutionStatus
    qualifying_report_id: UUID | None
    resolved_at: datetime | None
    ever_conflicted: bool


def _first_by_report_order(reports: Sequence[OutcomeReport]) -> OutcomeReport:
    return min(reports, key=lambda report: (report.reported_at, str(report.outcome_report_id)))


def derive_resolution(
    reports: Iterable[OutcomeReport],
    window: OutcomeWindow,
    now: datetime,
    *,
    previously_conflicted: bool = False,
) -> ResolutionOutcome:
    """Run the algorithm over the reports projected at the cutoff.

    `ever_conflicted` is monotonic: once two incompatible eligible reports have
    existed, no later correction makes the episode clean again.
    """

    eligible = [report for report in reports if report_is_eligible(report, window)]
    yes_reports = [report for report in eligible if report.value is OutcomeReportValue.YES]
    no_reports = [report for report in eligible if report.value is OutcomeReportValue.NO]

    if yes_reports and no_reports:
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.CONFLICTED,
            qualifying_report_id=None,
            resolved_at=None,
            ever_conflicted=True,
        )

    if yes_reports:
        qualifying = _first_by_report_order(yes_reports)
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.YES,
            qualifying_report_id=qualifying.outcome_report_id,
            resolved_at=qualifying.reported_at,
            ever_conflicted=previously_conflicted,
        )

    if no_reports:
        qualifying = _first_by_report_order(no_reports)
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.NO,
            qualifying_report_id=qualifying.outcome_report_id,
            resolved_at=qualifying.reported_at,
            ever_conflicted=previously_conflicted,
        )

    if now > window.capture_deadline_at:
        return ResolutionOutcome(
            status=OutcomeResolutionStatus.UNKNOWN,
            qualifying_report_id=None,
            resolved_at=window.capture_deadline_at,
            ever_conflicted=previously_conflicted,
        )

    return ResolutionOutcome(
        status=OutcomeResolutionStatus.PENDING,
        qualifying_report_id=None,
        resolved_at=None,
        ever_conflicted=previously_conflicted,
    )


def derive_request_state(
    resolution: OutcomeResolution, now: datetime, window: OutcomeWindow
) -> OutcomeRequestState:
    """Request state is a view of the active resolution and the clock.

    A pending resolution past the deadline is not `missing` yet: an `unknown`
    resolution is materialised first, and `missing` is derived from that.
    """

    if resolution.status in {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}:
        return OutcomeRequestState.REPORTED
    if resolution.status is OutcomeResolutionStatus.CONFLICTED:
        return OutcomeRequestState.CONFLICTED
    if resolution.status is OutcomeResolutionStatus.UNKNOWN:
        return OutcomeRequestState.MISSING
    if now <= window.capture_deadline_at:
        return OutcomeRequestState.OPEN
    raise ValueError(
        "a pending resolution past the deadline must first materialise an unknown resolution"
    )


def qualifies_for_primary_dataset(resolution: OutcomeResolution) -> bool:
    """Membership test, applied to the active resolution."""

    return (
        resolution.status in {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}
        and not resolution.ever_conflicted
        and resolution.qualifying_report_id is not None
    )
