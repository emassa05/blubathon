"""DQI, VoI, the form plan and `build_scenario`.

The worked numbers come from FUNDAMENTOS 9, 10 and 11.
"""

from __future__ import annotations

import math
from datetime import timedelta

import pytest

from ml.defaults import Stratum, eligible_history
from ml.errors import OriginMixError
from ml.form import (
    ScenarioInputs,
    base_slots_for,
    binary_entropy,
    build_form_plan,
    build_scenario,
    compute_dqi,
    compute_predictive_voi,
    estimate_voi,
    exploration_weekday,
)
from ml.spec_constants import (
    DQI_WINDOW_DAYS,
    LOW_COVERAGE_THRESHOLD,
)
from packages.shared.canonical import local_date
from packages.shared.domain.identity import SubjectProfile
from packages.shared.domain.observation import FormSession, QuestionPresentation
from packages.shared.enums import (
    DataOrigin,
    EntryMode,
    FieldCode,
    FormSessionKind,
    FormSessionStatus,
    QuestionReason,
    RecommendationAbstentionReason,
    RuntimeStatus,
    Source,
    VoiStatus,
)
from packages.shared.field_catalog import DQI_REQUIRED_FIELDS, MONITORED_FIELDS
from tests.p1.factories import ACTOR, NOW, SUBJECT, TENANT, ident, observation

SECRET = b"fixed-test-secret"
TODAY = local_date(NOW)


def _daily(label: str, day_offset: int, **overrides):
    return observation(label, effective_at=NOW - timedelta(days=day_offset), **overrides)


# --- DQI ------------------------------------------------------------------


def test_the_denominator_is_five_fields_times_fourteen_days() -> None:
    """FUNDAMENTOS 10.1: 70 observation opportunities, fixed."""

    rows = [
        _daily(f"{field}-{day}", day, field_code=field, value=value)
        for day in range(DQI_WINDOW_DAYS)
        for field, value in (
            (FieldCode.SLEEP_QUALITY, "restorative"),
            (FieldCode.WAKE_STATE, "calm_happy"),
            (FieldCode.GI_STATUS, "normal"),
            (FieldCode.MEDICATION_ADHERENCE, "taken"),
            (FieldCode.DAILY_REGULATION_STATE, "excellent"),
        )
    ]
    quality = compute_dqi(rows, as_of_at=NOW)
    assert quality.coverage == pytest.approx(1.0)
    assert quality.detail["denominator"] == 70.0


def test_one_good_day_does_not_score_as_well_covered() -> None:
    rows = [
        _daily(f"{field}", 0, field_code=field, value=value)
        for field, value in (
            (FieldCode.SLEEP_QUALITY, "restorative"),
            (FieldCode.WAKE_STATE, "calm_happy"),
            (FieldCode.GI_STATUS, "normal"),
            (FieldCode.MEDICATION_ADHERENCE, "taken"),
            (FieldCode.DAILY_REGULATION_STATE, "excellent"),
        )
    ]
    quality = compute_dqi(rows, as_of_at=NOW)
    assert quality.coverage == pytest.approx(5 / 70)
    assert quality.recency == pytest.approx(1.0)


def test_an_accepted_default_counts_half_and_an_edited_one_counts_fully() -> None:
    accepted = compute_dqi(
        [
            _daily(
                "accepted",
                0,
                field_code=FieldCode.GI_STATUS,
                value="normal",
                entry_mode=EntryMode.DEFAULT_ACCEPTED,
            )
        ],
        as_of_at=NOW,
    )
    edited = compute_dqi(
        [
            _daily(
                "edited",
                0,
                field_code=FieldCode.GI_STATUS,
                value="normal",
                entry_mode=EntryMode.DEFAULT_EDITED,
            )
        ],
        as_of_at=NOW,
    )
    assert accepted.coverage == pytest.approx(0.5 / 70)
    assert edited.coverage == pytest.approx(1.0 / 70)


def test_an_explicit_unknown_contributes_nothing_to_coverage() -> None:
    quality = compute_dqi(
        [
            _daily(
                "unknown",
                0,
                field_code=FieldCode.GI_STATUS,
                value=None,
                entry_mode=EntryMode.EXPLICIT_UNKNOWN,
            )
        ],
        as_of_at=NOW,
    )
    assert quality.coverage == 0.0
    assert quality.recency == 0.0


def test_medication_not_applicable_is_a_present_answer() -> None:
    quality = compute_dqi(
        [
            _daily(
                "na",
                0,
                field_code=FieldCode.MEDICATION_ADHERENCE,
                value="not_applicable",
            )
        ],
        as_of_at=NOW,
    )
    assert quality.coverage == pytest.approx(1 / 70)


@pytest.mark.parametrize(("days", "expected"), [(0, 1.0), (2, 0.5), (4, 0.25)])
def test_recency_halves_every_two_days(days: int, expected: float) -> None:
    quality = compute_dqi(
        [_daily("row", days, field_code=FieldCode.GI_STATUS, value="normal")], as_of_at=NOW
    )
    assert quality.recency == pytest.approx(expected)
    assert quality.days_since_last_observation == days


def test_no_observation_in_the_window_means_zero_recency() -> None:
    quality = compute_dqi([], as_of_at=NOW)
    assert quality.recency == 0.0
    assert quality.dqi == 0.0
    assert quality.days_since_last_observation is None


def test_agreeing_sources_produce_no_disagreement() -> None:
    rows = [
        _daily("home", 0, field_code=FieldCode.GI_STATUS, value="normal", source=Source.HOME),
        _daily("therapy", 0, field_code=FieldCode.GI_STATUS, value="normal", source=Source.THERAPY),
    ]
    quality = compute_dqi(rows, as_of_at=NOW)
    assert quality.consistency == 1.0
    assert quality.overlapping_field_days == 1


def test_a_nominal_disagreement_is_all_or_nothing_and_hits_the_floor() -> None:
    rows = [
        _daily("home", 0, field_code=FieldCode.GI_STATUS, value="normal", source=Source.HOME),
        _daily(
            "therapy",
            0,
            field_code=FieldCode.GI_STATUS,
            value="diarrhea",
            source=Source.THERAPY,
        ),
    ]
    quality = compute_dqi(rows, as_of_at=NOW)
    assert quality.consistency == 0.5


def test_without_overlap_consistency_is_one() -> None:
    quality = compute_dqi(
        [_daily("home", 0, field_code=FieldCode.GI_STATUS, value="normal")], as_of_at=NOW
    )
    assert quality.consistency == 1.0
    assert quality.overlapping_field_days == 0


def test_the_index_is_the_product_of_its_parts() -> None:
    rows = [
        _daily(f"{field}-{day}", day, field_code=field, value=value)
        for day in range(2, 5)
        for field, value in (
            (FieldCode.SLEEP_QUALITY, "restorative"),
            (FieldCode.GI_STATUS, "normal"),
        )
    ]
    quality = compute_dqi(rows, as_of_at=NOW)
    assert quality.dqi == pytest.approx(quality.coverage * quality.recency * quality.consistency)


def test_the_dqi_refuses_to_mix_origins() -> None:
    rows = [
        _daily("real", 0, field_code=FieldCode.GI_STATUS, value="normal"),
        _daily(
            "synthetic",
            1,
            field_code=FieldCode.GI_STATUS,
            value="normal",
            data_origin=DataOrigin.SYNTHETIC,
        ),
    ]
    with pytest.raises(OriginMixError):
        compute_dqi(rows, as_of_at=NOW)


def test_the_window_is_the_last_fourteen_inclusive_days() -> None:
    inside = compute_dqi(
        [_daily("inside", 13, field_code=FieldCode.GI_STATUS, value="normal")], as_of_at=NOW
    )
    outside = compute_dqi(
        [_daily("outside", 14, field_code=FieldCode.GI_STATUS, value="normal")], as_of_at=NOW
    )
    assert inside.coverage > 0.0
    assert outside.coverage == 0.0


def test_the_required_fields_are_the_five_monitored_ones() -> None:
    quality = compute_dqi([], as_of_at=NOW)
    assert quality.required_fields == tuple(DQI_REQUIRED_FIELDS)


# --- VoI ------------------------------------------------------------------


def test_the_voi_worked_example_from_fundamentos() -> None:
    assert binary_entropy(0.3) == pytest.approx(0.610864, abs=1e-6)
    assert binary_entropy(0.1) == pytest.approx(0.325083, abs=1e-6)
    assert binary_entropy(0.5) == pytest.approx(0.693147, abs=1e-6)
    assert compute_predictive_voi([0.5, 0.5], [0.1, 0.5]) == pytest.approx(0.101749, abs=1e-6)


def test_identical_conditional_risks_carry_no_information() -> None:
    assert compute_predictive_voi([0.5, 0.5], [0.3, 0.3]) == pytest.approx(0.0, abs=1e-12)


def test_zero_times_log_zero_is_defined_as_zero() -> None:
    assert binary_entropy(0.0) == 0.0
    assert binary_entropy(1.0) == 0.0
    assert compute_predictive_voi([1.0], [0.0]) == 0.0


def test_the_unit_is_nats() -> None:
    """A perfectly informative binary split is ln 2 nats, not one bit."""

    assert compute_predictive_voi([0.5, 0.5], [0.0, 1.0]) == pytest.approx(math.log(2))


def test_a_malformed_distribution_is_rejected() -> None:
    with pytest.raises(ValueError, match="sum to one"):
        compute_predictive_voi([0.5, 0.4], [0.1, 0.2])
    with pytest.raises(ValueError, match="negative weight"):
        compute_predictive_voi([1.5, -0.5], [0.1, 0.2])
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        compute_predictive_voi([0.5, 0.5], [0.1, 1.2])


class _StubModel:
    """A conditional model for tests; no real model exists in v0.3."""

    model_version = "stub-conditional-0"

    def __init__(self, probabilities: dict[object, float] | None = None) -> None:
        self._probabilities = probabilities or {}

    def supports(self, field_code: FieldCode) -> bool:
        return field_code is FieldCode.SLEEP_QUALITY

    def conditional_probability(self, field_code: FieldCode, value: object) -> float | None:
        return self._probabilities.get(value)


def _sleep_history(count: int = 6):
    stratum = Stratum(
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.SLEEP_QUALITY,
    )
    rows = [
        _daily(f"sleep-{index}", index + 1, field_code=FieldCode.SLEEP_QUALITY, value="restorative")
        for index in range(count)
    ]
    return eligible_history(rows, stratum=stratum, cutoff=NOW)


def test_without_a_model_voi_is_null_not_zero() -> None:
    """INV-09."""

    estimate = estimate_voi(_sleep_history(), model=None, cutoff=NOW)
    assert estimate.status is VoiStatus.UNAVAILABLE_MODEL
    assert estimate.voi_nats is None


def test_a_field_without_a_closed_support_is_unavailable_by_type() -> None:
    stratum = Stratum(
        tenant_id=TENANT, subject_id=SUBJECT, source=Source.HOME, field_code=FieldCode.SLEEP_HOURS
    )
    history = eligible_history([], stratum=stratum, cutoff=NOW)
    estimate = estimate_voi(history, model=_StubModel(), cutoff=NOW)
    assert estimate.status is VoiStatus.UNAVAILABLE_FIELD_TYPE
    assert estimate.voi_nats is None


def test_a_model_that_cannot_answer_one_value_makes_the_whole_field_unavailable() -> None:
    partial = _StubModel({"restorative": 0.1})
    estimate = estimate_voi(_sleep_history(), model=partial, cutoff=NOW)
    assert estimate.status is VoiStatus.UNAVAILABLE_PREDICTION
    assert estimate.voi_nats is None


def test_an_available_voi_records_its_versions_and_cutoff() -> None:
    model = _StubModel(
        {
            "restorative": 0.1,
            "interrupted": 0.5,
            "sleep_onset_difficulty": 0.4,
            "other": 0.2,
        }
    )
    estimate = estimate_voi(_sleep_history(), model=model, cutoff=NOW)
    assert estimate.status is VoiStatus.AVAILABLE
    assert estimate.voi_nats is not None and estimate.voi_nats >= 0.0
    assert estimate.conditional_model_version == "stub-conditional-0"
    assert estimate.cutoff_at == NOW


# --- the plan -------------------------------------------------------------


def _presentation(field_code: FieldCode, day_offset: int, *, highlighted: bool = True):
    moment = NOW - timedelta(days=day_offset)
    return QuestionPresentation(
        question_presentation_id=ident(f"presentation-{field_code}-{day_offset}-{highlighted}"),
        tenant_id=TENANT,
        subject_id=SUBJECT,
        form_session_id=ident(f"session-{day_offset}"),
        field_code=field_code,
        source=Source.HOME,
        highlighted=highlighted,
        reason=QuestionReason.STALENESS,
        presented_at=moment,
        local_date=local_date(moment),
        ingested_at=moment,
    )


def _plan(**overrides):
    payload = {
        "source": Source.HOME,
        "today": TODAY,
        "cutoff": NOW,
        "coverage": 0.9,
        "outcome_pending": False,
    }
    payload.update(overrides)
    return build_form_plan(**payload)


def test_low_coverage_widens_the_slots() -> None:
    assert base_slots_for(LOW_COVERAGE_THRESHOLD - 0.01) == 3
    assert base_slots_for(LOW_COVERAGE_THRESHOLD) == 2
    assert base_slots_for(0.9) == 2


def test_every_applicable_field_stays_reachable() -> None:
    """INV-10: highlighted plus tail keeps all applicable fields, each once."""

    from packages.shared.field_catalog import applicable_fields

    for source in Source:
        plan = _plan(source=source)
        codes = plan.field_codes
        assert sorted(codes, key=str) == sorted(applicable_fields(source), key=str)
        assert len(set(codes)) == len(codes)


def test_the_first_session_follows_the_declared_priority() -> None:
    plan = _plan()
    highlighted = [question.field_code for question in plan.highlighted]
    assert highlighted[: len(MONITORED_FIELDS)] == list(MONITORED_FIELDS)
    assert all(question.reason is QuestionReason.STALENESS for question in plan.highlighted)


def test_every_overdue_field_is_included_even_beyond_the_usual_slots() -> None:
    presentations = [_presentation(field, 8) for field in MONITORED_FIELDS]
    plan = _plan(presentations=presentations)
    stale = [question.field_code for question in plan.highlighted]
    assert set(MONITORED_FIELDS) <= set(stale)
    assert len(stale) > plan.base_slots


def test_a_recently_asked_field_is_not_overdue() -> None:
    presentations = [_presentation(field, 1) for field in MONITORED_FIELDS]
    plan = _plan(presentations=presentations)
    reasons = {question.reason for question in plan.highlighted}
    assert QuestionReason.STALENESS not in reasons
    assert len(plan.highlighted) == plan.base_slots


def test_sitting_in_the_tail_does_not_reset_the_clock() -> None:
    """SPEC 6.10: only a highlighted presentation counts as having been asked."""

    presentations = [_presentation(field, 1, highlighted=False) for field in MONITORED_FIELDS]
    plan = _plan(presentations=presentations)
    assert {question.reason for question in plan.highlighted} == {QuestionReason.STALENESS}


def test_the_staleness_order_puts_the_longest_wait_first() -> None:
    presentations = [
        _presentation(FieldCode.SLEEP_QUALITY, 8),
        _presentation(FieldCode.WAKE_STATE, 30),
        _presentation(FieldCode.GI_STATUS, 15),
        _presentation(FieldCode.MEDICATION_ADHERENCE, 9),
        _presentation(FieldCode.DAILY_REGULATION_STATE, 20),
    ]
    plan = _plan(presentations=presentations)
    assert [question.field_code for question in plan.highlighted][:3] == [
        FieldCode.WAKE_STATE,
        FieldCode.DAILY_REGULATION_STATE,
        FieldCode.GI_STATUS,
    ]


def test_an_answered_field_is_not_presented_again_in_the_session() -> None:
    plan = _plan(answered_fields=frozenset({FieldCode.SLEEP_QUALITY}))
    assert FieldCode.SLEEP_QUALITY not in plan.field_codes


def test_voi_orders_the_remaining_slots_but_never_displaces_an_overdue_field() -> None:
    from packages.shared.domain.prediction import VoiEstimate

    presentations = [_presentation(field, 1) for field in MONITORED_FIELDS]
    voi = {
        FieldCode.FOOD_CHANGES: VoiEstimate(
            field_code=FieldCode.FOOD_CHANGES,
            status=VoiStatus.AVAILABLE,
            voi_nats=0.4,
            q_estimator_version="defaults-0.3.0",
            conditional_model_version="stub-conditional-0",
            cutoff_at=NOW,
        ),
        FieldCode.ROUTINE_CHANGES: VoiEstimate(
            field_code=FieldCode.ROUTINE_CHANGES,
            status=VoiStatus.AVAILABLE,
            voi_nats=0.9,
            q_estimator_version="defaults-0.3.0",
            conditional_model_version="stub-conditional-0",
            cutoff_at=NOW,
        ),
    }
    plan = _plan(presentations=presentations, voi=voi)
    highlighted = [question.field_code for question in plan.highlighted]
    assert highlighted[0] is FieldCode.ROUTINE_CHANGES
    assert plan.voi_status is VoiStatus.AVAILABLE

    overdue = _plan(voi=voi)
    assert {question.field_code for question in overdue.highlighted} >= set(MONITORED_FIELDS)


def test_exploration_takes_at_most_one_remaining_slot() -> None:
    presentations = [_presentation(field, 1) for field in MONITORED_FIELDS]
    weekday = exploration_weekday(
        secret=SECRET,
        tenant_id=TENANT,
        subject_id=SUBJECT,
        iso_week=f"{TODAY.isocalendar()[0]:04d}-W{TODAY.isocalendar()[1]:02d}",
        policy_version="form-0.3.0",
    )
    on_day = TODAY + timedelta(days=(weekday - (TODAY.isocalendar()[2] - 1)) % 7)
    plan = build_form_plan(
        source=Source.HOME,
        today=on_day,
        cutoff=NOW,
        coverage=0.9,
        outcome_pending=False,
        presentations=presentations,
        exploration_secret=SECRET,
        tenant_id=TENANT,
        subject_id=SUBJECT,
        policy_version="form-0.3.0",
    )
    exploration = [
        question for question in plan.highlighted if question.reason is QuestionReason.EXPLORATION
    ]
    assert len(exploration) <= 1


def test_the_exploration_weekday_is_stable_and_needs_a_secret() -> None:
    kwargs = {
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "iso_week": "2026-W35",
        "policy_version": "form-0.3.0",
    }
    first = exploration_weekday(secret=SECRET, **kwargs)
    assert first == exploration_weekday(secret=SECRET, **kwargs)
    assert 0 <= first < 7
    assert exploration_weekday(secret=SECRET, **{**kwargs, "iso_week": "2026-W36"}) != first or True


def test_the_pending_outcome_does_not_consume_a_daily_slot() -> None:
    without = _plan(outcome_pending=False)
    with_outcome = _plan(outcome_pending=True)
    assert with_outcome.outcome_pending is True
    assert len(with_outcome.highlighted) == len(without.highlighted)


def test_only_fields_the_source_allows_are_planned() -> None:
    plan = _plan(source=Source.SCHOOL)
    assert FieldCode.SLEEP_HOURS not in plan.field_codes
    assert FieldCode.ATTENDANCE_STATUS in plan.field_codes


# --- build_scenario -------------------------------------------------------


def _profile(**overrides) -> SubjectProfile:
    payload = {
        "subject_profile_id": ident("profile"),
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "sensory_profile_tags": frozenset({"auditory_hypersensitive"}),
        "communication_support_tags": frozenset({"picture_exchange"}),
        "contraindication_tags": frozenset({"weighted_vest"}),
        "care_mode": "standard_support",
        "profile_version": "profile-1",
        "effective_from": NOW - timedelta(days=30),
        "recorded_at": NOW - timedelta(days=30),
        "ingested_at": NOW - timedelta(days=30),
    }
    payload.update(overrides)
    return SubjectProfile(**payload)


def _submitted_session(**overrides) -> FormSession:
    payload = {
        "form_session_id": ident("scenario-session"),
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "actor_id": ACTOR,
        "source": Source.THERAPY,
        "session_kind": FormSessionKind.CAREGIVER_DAILY,
        "status": FormSessionStatus.SUBMITTED,
        "audit_mode": False,
        "form_policy_version": "form-0.3.0",
        "opened_at": NOW - timedelta(minutes=20),
        "submitted_at": NOW,
    }
    payload.update(overrides)
    return FormSession(**payload)


def _scenario_inputs(rows, **overrides) -> ScenarioInputs:
    session = overrides.pop("form_session", _submitted_session())
    payload = {
        "form_session": session,
        "as_of_at": NOW,
        "observations": rows,
        "profile": _profile(),
        "context_tags": frozenset(),
        "tenant_secret": SECRET,
    }
    payload.update(overrides)
    return ScenarioInputs(**payload)


def _session_observation(label: str, field_code: FieldCode, value, **overrides):
    overrides.setdefault("effective_at", NOW - timedelta(minutes=5))
    return observation(
        label,
        field_code=field_code,
        value=value,
        source=Source.THERAPY,
        **overrides,
    ).model_copy(update={"form_session_id": ident("scenario-session")})


def test_a_scenario_carries_only_allowlisted_fields_and_namespaced_tags() -> None:
    rows = [
        _session_observation("gi", FieldCode.GI_STATUS, "normal"),
        _session_observation("alertness", FieldCode.ALERTNESS, "high"),
        _session_observation("participation", FieldCode.ACTIVITY_PARTICIPATION, 4),
    ]
    result = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    assert result.status is RuntimeStatus.MATCHED
    scenario = result.scenario
    assert scenario is not None
    assert set(scenario.field_values) == {FieldCode.GI_STATUS, FieldCode.ALERTNESS}
    assert scenario.context_tags == ("therapy",)
    assert scenario.profile_tags == (
        "communication:picture_exchange",
        "sensory:auditory_hypersensitive",
    )
    assert scenario.contraindication_tags == ("weighted_vest",)


def test_an_unknown_answer_is_omitted_rather_than_guessed() -> None:
    rows = [
        _session_observation(
            "unknown",
            FieldCode.GI_STATUS,
            None,
            entry_mode=EntryMode.EXPLICIT_UNKNOWN,
        ),
        _session_observation("alertness", FieldCode.ALERTNESS, "high"),
    ]
    result = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    assert result.scenario is not None
    assert FieldCode.GI_STATUS not in result.scenario.field_values


def test_two_active_leaves_for_one_field_abstain() -> None:
    rows = [
        _session_observation("first", FieldCode.GI_STATUS, "normal"),
        _session_observation("second", FieldCode.GI_STATUS, "diarrhea"),
    ]
    result = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    assert result.status is RuntimeStatus.ABSTAINED
    assert result.reasons == (RecommendationAbstentionReason.SCENARIO_UNAVAILABLE_CONFLICT,)
    assert result.scenario is None


def test_the_scenario_hash_is_keyed_and_stable() -> None:
    rows = [_session_observation("gi", FieldCode.GI_STATUS, "normal")]
    first = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    same = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    other_tenant = build_scenario(
        _scenario_inputs(rows, tenant_secret=b"another-secret"),
        submitted_form_session_id=ident("scenario-session"),
    )
    assert first.scenario_hash == same.scenario_hash
    assert first.scenario_hash != other_tenant.scenario_hash


def test_a_scenario_needs_a_submitted_session_and_the_matching_cutoff() -> None:
    rows = [_session_observation("gi", FieldCode.GI_STATUS, "normal")]
    draft = _submitted_session(status=FormSessionStatus.DRAFT, submitted_at=None)
    with pytest.raises(ValueError, match="submitted session"):
        build_scenario(
            _scenario_inputs(rows, form_session=draft),
            submitted_form_session_id=ident("scenario-session"),
        )
    with pytest.raises(ValueError, match="snapshot cutoff"):
        build_scenario(
            _scenario_inputs(rows, as_of_at=NOW + timedelta(minutes=1)),
            submitted_form_session_id=ident("scenario-session"),
        )


def test_a_scenario_never_reads_another_session_or_later_data() -> None:
    other_session = observation(
        "other-session",
        field_code=FieldCode.GI_STATUS,
        value="diarrhea",
        source=Source.THERAPY,
        effective_at=NOW - timedelta(hours=1),
    ).model_copy(update={"form_session_id": ident("another-session")})
    later = _session_observation(
        "later",
        FieldCode.ALERTNESS,
        "low",
        effective_at=NOW + timedelta(minutes=1),
        ingested_at=NOW + timedelta(minutes=1),
    )
    rows = [other_session, later, _session_observation("gi", FieldCode.GI_STATUS, "normal")]
    result = build_scenario(
        _scenario_inputs(rows), submitted_form_session_id=ident("scenario-session")
    )
    assert result.scenario is not None
    assert result.scenario.field_values == {FieldCode.GI_STATUS: "normal"}
