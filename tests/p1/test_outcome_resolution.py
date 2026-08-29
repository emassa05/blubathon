"""Timing, eligibility and resolution of outcomes.

The distinctions these tests protect are the ones that matter most: absence
is not a negative, an explicit `unknown` resolves nothing, a reported `no`
resolves as soon as it is given, and once an episode has conflicted it never
becomes clean again.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from packages.shared.domain.outcome import (
    OutcomeResolution,
    classify_timing,
    derive_request_state,
    derive_resolution,
    qualifies_for_primary_dataset,
    report_is_eligible,
)
from packages.shared.enums import (
    OutcomeReportValue,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    Role,
    TimingStatus,
)
from tests.p1.factories import NOW, TENANT, ident, report, window

WINDOW = window()
INSIDE = NOW + timedelta(hours=5)
BEFORE_END = NOW + timedelta(hours=20)
AT_END = WINDOW.target_end_at
AT_DEADLINE = WINDOW.capture_deadline_at
AFTER_DEADLINE = AT_DEADLINE + timedelta(seconds=1)


def _resolution(status: OutcomeResolutionStatus, **overrides: object) -> OutcomeResolution:
    payload: dict[str, object] = {
        "outcome_resolution_id": ident("resolution"),
        "tenant_id": TENANT,
        "prediction_episode_id": ident("episode"),
        "status": status,
        "ever_conflicted": status is OutcomeResolutionStatus.CONFLICTED,
        "resolution_version": 1,
        "ingested_at": NOW,
    }
    payload.update(overrides)
    return OutcomeResolution(**payload)


# --- timing ---------------------------------------------------------------


def test_timing_boundaries_are_exact() -> None:
    assert classify_timing(BEFORE_END, WINDOW) is TimingStatus.EARLY
    assert classify_timing(AT_END - timedelta(seconds=1), WINDOW) is TimingStatus.EARLY
    assert classify_timing(AT_END, WINDOW) is TimingStatus.ON_TIME
    assert classify_timing(AT_DEADLINE, WINDOW) is TimingStatus.ON_TIME
    assert classify_timing(AFTER_DEADLINE, WINDOW) is TimingStatus.LATE


# --- eligibility ----------------------------------------------------------


def test_an_early_yes_inside_the_window_is_eligible() -> None:
    early_yes = report(
        "early-yes", value=OutcomeReportValue.YES, reported_at=BEFORE_END, occurred_at=INSIDE
    )
    assert early_yes.timing_status is TimingStatus.EARLY
    assert report_is_eligible(early_yes, WINDOW)


def test_a_yes_whose_event_falls_outside_the_window_is_not_eligible() -> None:
    outside = report(
        "outside-yes",
        value=OutcomeReportValue.YES,
        reported_at=AT_END,
        occurred_at=NOW - timedelta(hours=1),
    )
    assert not report_is_eligible(outside, WINDOW)


def test_the_window_start_is_open_so_an_event_at_the_cutoff_is_not_a_label() -> None:
    """The open start stops a fact used in the snapshot from being the label."""

    at_cutoff = report(
        "at-cutoff", value=OutcomeReportValue.YES, reported_at=AT_END, occurred_at=NOW
    )
    assert not report_is_eligible(at_cutoff, WINDOW)


def test_an_early_no_is_eligible() -> None:
    """An early `no` resolves, and is still recorded as having arrived early.

    It used to stay provisional on the grounds that it cannot know about the
    rest of the window. Accepting it and then ignoring it gives the caregiver
    nothing back, so the report now counts; `timing_status` keeps the fact that
    it came in before the window closed.
    """

    early_no = report("early-no", value=OutcomeReportValue.NO, reported_at=BEFORE_END)
    assert early_no.timing_status is TimingStatus.EARLY
    assert report_is_eligible(early_no, WINDOW)


def test_an_on_time_no_is_eligible() -> None:
    on_time_no = report("on-time-no", value=OutcomeReportValue.NO, reported_at=AT_END)
    assert report_is_eligible(on_time_no, WINDOW)


def test_an_unknown_report_is_never_eligible() -> None:
    unknown = report("unknown", value=OutcomeReportValue.UNKNOWN, reported_at=AT_END)
    assert not report_is_eligible(unknown, WINDOW)


def test_a_late_report_is_kept_but_never_eligible() -> None:
    late = report(
        "late", value=OutcomeReportValue.YES, reported_at=AFTER_DEADLINE, occurred_at=INSIDE
    )
    assert late.timing_status is TimingStatus.LATE
    assert not report_is_eligible(late, WINDOW)


# --- resolution -----------------------------------------------------------


def test_no_report_before_the_deadline_stays_pending() -> None:
    outcome = derive_resolution([], WINDOW, now=BEFORE_END)
    assert outcome.status is OutcomeResolutionStatus.PENDING
    assert outcome.resolved_at is None


def test_absence_at_the_deadline_becomes_unknown_never_no() -> None:
    outcome = derive_resolution([], WINDOW, now=AFTER_DEADLINE)
    assert outcome.status is OutcomeResolutionStatus.UNKNOWN
    assert outcome.qualifying_report_id is None
    assert outcome.resolved_at == AT_DEADLINE


def test_an_explicit_unknown_leaves_the_resolution_pending() -> None:
    unknown = report("unknown", value=OutcomeReportValue.UNKNOWN, reported_at=AT_END)
    outcome = derive_resolution([unknown], WINDOW, now=AT_END)
    assert outcome.status is OutcomeResolutionStatus.PENDING


def test_an_early_no_resolves_before_the_window_closes() -> None:
    early_no = report("early-no", value=OutcomeReportValue.NO, reported_at=BEFORE_END)
    outcome = derive_resolution([early_no], WINDOW, now=BEFORE_END)
    assert outcome.status is OutcomeResolutionStatus.NO
    assert outcome.qualifying_report_id == early_no.outcome_report_id


def test_a_late_no_is_still_not_eligible() -> None:
    """Nothing changed past the deadline: there the episode already resolved."""

    late_no = report("late-no", value=OutcomeReportValue.NO, reported_at=AFTER_DEADLINE)
    assert late_no.timing_status is TimingStatus.LATE
    assert not report_is_eligible(late_no, WINDOW)


def test_a_valid_early_yes_resolves_before_the_window_closes() -> None:
    early_yes = report(
        "early-yes", value=OutcomeReportValue.YES, reported_at=BEFORE_END, occurred_at=INSIDE
    )
    outcome = derive_resolution([early_yes], WINDOW, now=BEFORE_END)
    assert outcome.status is OutcomeResolutionStatus.YES
    assert outcome.qualifying_report_id == early_yes.outcome_report_id


def test_incompatible_eligible_reports_conflict() -> None:
    yes = report("yes", value=OutcomeReportValue.YES, reported_at=BEFORE_END, occurred_at=INSIDE)
    no = report("no", value=OutcomeReportValue.NO, reported_at=AT_END)
    outcome = derive_resolution([yes, no], WINDOW, now=AT_END)
    assert outcome.status is OutcomeResolutionStatus.CONFLICTED
    assert outcome.ever_conflicted is True
    assert outcome.qualifying_report_id is None


def test_ever_conflicted_is_monotonic_across_corrections() -> None:
    yes = report("yes", value=OutcomeReportValue.YES, reported_at=BEFORE_END, occurred_at=INSIDE)
    outcome = derive_resolution([yes], WINDOW, now=AT_END, previously_conflicted=True)
    assert outcome.status is OutcomeResolutionStatus.YES
    assert outcome.ever_conflicted is True


def test_the_qualifying_report_is_the_first_by_report_order() -> None:
    first = report("first", value=OutcomeReportValue.YES, reported_at=INSIDE, occurred_at=INSIDE)
    second = report(
        "second", value=OutcomeReportValue.YES, reported_at=BEFORE_END, occurred_at=INSIDE
    )
    outcome = derive_resolution([second, first], WINDOW, now=AT_END)
    assert outcome.qualifying_report_id == first.outcome_report_id


def test_a_late_report_does_not_resolve_the_episode() -> None:
    late = report(
        "late", value=OutcomeReportValue.YES, reported_at=AFTER_DEADLINE, occurred_at=INSIDE
    )
    outcome = derive_resolution([late], WINDOW, now=AFTER_DEADLINE)
    assert outcome.status is OutcomeResolutionStatus.UNKNOWN


# --- persisted resolution -------------------------------------------------


def test_a_conclusive_resolution_names_its_qualifying_report() -> None:
    with pytest.raises(ValidationError):
        _resolution(OutcomeResolutionStatus.YES)
    assert _resolution(
        OutcomeResolutionStatus.YES,
        qualifying_report_id=ident("report"),
        resolved_at=INSIDE,
    )


def test_a_pending_resolution_has_no_resolved_at() -> None:
    with pytest.raises(ValidationError):
        _resolution(OutcomeResolutionStatus.PENDING, resolved_at=INSIDE)


def test_a_conflicted_resolution_is_by_definition_ever_conflicted() -> None:
    with pytest.raises(ValidationError):
        _resolution(OutcomeResolutionStatus.CONFLICTED, ever_conflicted=False)


# --- derived request state -----------------------------------------------


def test_request_state_is_derived_from_the_resolution_and_the_clock() -> None:
    pending = _resolution(OutcomeResolutionStatus.PENDING)
    assert derive_request_state(pending, BEFORE_END, WINDOW) is OutcomeRequestState.OPEN

    reported = _resolution(
        OutcomeResolutionStatus.YES,
        qualifying_report_id=ident("report"),
        resolved_at=INSIDE,
    )
    assert derive_request_state(reported, AT_END, WINDOW) is OutcomeRequestState.REPORTED

    conflicted = _resolution(OutcomeResolutionStatus.CONFLICTED)
    assert derive_request_state(conflicted, AT_END, WINDOW) is OutcomeRequestState.CONFLICTED

    unknown = _resolution(OutcomeResolutionStatus.UNKNOWN, resolved_at=AT_DEADLINE)
    assert derive_request_state(unknown, AFTER_DEADLINE, WINDOW) is OutcomeRequestState.MISSING


def test_a_pending_resolution_past_the_deadline_must_materialise_unknown_first() -> None:
    pending = _resolution(OutcomeResolutionStatus.PENDING)
    with pytest.raises(ValueError, match="materialise an unknown resolution"):
        derive_request_state(pending, AFTER_DEADLINE, WINDOW)


# --- dataset membership ---------------------------------------------------


def test_an_ever_conflicted_episode_stays_out_of_the_primary_dataset() -> None:
    resolved_after_conflict = _resolution(
        OutcomeResolutionStatus.NO,
        qualifying_report_id=ident("report"),
        resolved_at=AT_END,
        ever_conflicted=True,
        resolution_version=2,
    )
    assert resolved_after_conflict.excluded_from_primary_dataset
    assert not qualifies_for_primary_dataset(resolved_after_conflict)


def test_a_clean_conclusive_resolution_qualifies() -> None:
    clean = _resolution(
        OutcomeResolutionStatus.NO,
        qualifying_report_id=ident("report"),
        resolved_at=AT_END,
    )
    assert qualifies_for_primary_dataset(clean)


def test_unknown_never_qualifies() -> None:
    unknown = _resolution(OutcomeResolutionStatus.UNKNOWN, resolved_at=AT_DEADLINE)
    assert not qualifies_for_primary_dataset(unknown)


# --- report shape ---------------------------------------------------------


def test_only_a_yes_report_states_when_the_event_happened() -> None:
    with pytest.raises(ValidationError):
        report(
            "no-with-occurred",
            value=OutcomeReportValue.NO,
            reported_at=AT_END,
            occurred_at=INSIDE,
        )
    with pytest.raises(ValidationError):
        report("yes-without-occurred", value=OutcomeReportValue.YES, reported_at=AT_END)


def test_an_event_cannot_occur_after_it_was_reported() -> None:
    with pytest.raises(ValidationError):
        report(
            "backwards",
            value=OutcomeReportValue.YES,
            reported_at=INSIDE,
            occurred_at=BEFORE_END,
        )


def test_the_reporter_role_is_recorded_on_every_report() -> None:
    stored = report(
        "professional",
        value=OutcomeReportValue.NO,
        reported_at=AT_END,
        reporter_role=Role.PROFESSIONAL,
    )
    assert stored.reporter_role is Role.PROFESSIONAL
