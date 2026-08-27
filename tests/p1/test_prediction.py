"""Dual-track prediction: simulation, personal baseline and shadow challenger."""

from __future__ import annotations

from datetime import timedelta

import pytest
from scipy.stats import beta as beta_dist

from ml.errors import CohortViolationError
from ml.prediction import (
    BaselineCandidate,
    ChallengerRow,
    assess_trainability,
    build_personal_baseline,
    encode_predictor,
    fit_challenger,
    logit,
    negative_log_likelihood,
    personal_predictor_rate,
    score_simulation,
    select_penalty,
    sigmoid,
    train_challenger,
)
from ml.spec_constants import BASELINE_MIN_OUTCOMES, CHALLENGER_L2_GRID
from packages.shared.domain.outcome import OutcomeResolution
from packages.shared.enums import (
    CohortKind,
    DataOrigin,
    FieldCode,
    NotTrainableReason,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
    Source,
)
from tests.p1.factories import NOW, SUBJECT, TENANT, episode, ident, observation

CARE_MODE = "standard_support"
TARGET_VERSION = "target-demo-1"


# --- simulation track -----------------------------------------------------


class _StubArtifact:
    model_version = "synthetic-reference-0.2.1"

    def score(self, features: dict[str, float]) -> float:
        return 0.42


def test_the_simulation_track_refuses_a_real_subject() -> None:
    """INV-18."""

    with pytest.raises(CohortViolationError):
        score_simulation(
            {},
            cohort_kind=CohortKind.REAL_SUBJECT,
            input_data_origin=DataOrigin.SYNTHETIC,
            artifact=_StubArtifact(),
        )


def test_the_simulation_track_refuses_real_input_data() -> None:
    with pytest.raises(CohortViolationError):
        score_simulation(
            {},
            cohort_kind=CohortKind.DEMO_FIXTURE,
            input_data_origin=DataOrigin.REAL,
            artifact=_StubArtifact(),
        )


def test_a_simulation_score_is_never_a_probability() -> None:
    result = score_simulation(
        {},
        cohort_kind=CohortKind.DEMO_FIXTURE,
        input_data_origin=DataOrigin.SYNTHETIC,
        artifact=_StubArtifact(),
    )
    assert result.status is PredictionStatus.OK
    assert result.simulation_score == 0.42
    assert result.probability is None
    assert result.intended_use.value == "simulation_only"


def test_a_missing_artifact_is_unavailable_not_zero() -> None:
    result = score_simulation(
        {},
        cohort_kind=CohortKind.DEMO_FIXTURE,
        input_data_origin=DataOrigin.SYNTHETIC,
        artifact=None,
    )
    assert result.status is PredictionStatus.UNAVAILABLE
    assert result.simulation_score is None
    assert result.abstention_reasons == (PredictionAbstentionReason.MODEL_ARTIFACT_UNAVAILABLE,)


# --- personal baseline ----------------------------------------------------


def _candidate(
    label: str,
    *,
    outcome: OutcomeResolutionStatus,
    days_ago: int = 5,
    care_mode: str = CARE_MODE,
    target_version: str = TARGET_VERSION,
    ever_conflicted: bool = False,
    consent: bool = True,
    resolved_offset_hours: int = 30,
    data_origin: DataOrigin = DataOrigin.REAL,
) -> BaselineCandidate:
    start = NOW - timedelta(days=days_ago)
    built = episode(label, prediction_at=start, data_origin=data_origin)
    built = built.model_copy(
        update={"care_mode": care_mode, "target_definition_version": target_version}
    )
    conclusive = outcome in {OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO}
    resolution = OutcomeResolution(
        outcome_resolution_id=ident(f"resolution-{label}"),
        tenant_id=TENANT,
        prediction_episode_id=built.prediction_episode_id,
        status=outcome,
        resolved_at=start + timedelta(hours=resolved_offset_hours) if conclusive else None,
        qualifying_report_id=ident(f"report-{label}") if conclusive else None,
        ever_conflicted=ever_conflicted or outcome is OutcomeResolutionStatus.CONFLICTED,
        resolution_version=1,
        ingested_at=start + timedelta(hours=resolved_offset_hours),
    )
    return BaselineCandidate(episode=built, resolution=resolution, consent_authorized=consent)


def _baseline(candidates, **overrides):
    payload = {
        "as_of_at": NOW,
        "subject_id": SUBJECT,
        "care_mode": CARE_MODE,
        "target_definition_version": TARGET_VERSION,
    }
    payload.update(overrides)
    return build_personal_baseline(candidates, **payload)


def test_fewer_than_five_verified_outcomes_abstains() -> None:
    """INV-20."""

    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(BASELINE_MIN_OUTCOMES - 1)
    ]
    estimate = _baseline(candidates)
    assert estimate.status is PredictionStatus.ABSTAINED
    assert PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES in (
        estimate.abstention_reasons
    )
    assert estimate.probability is None and estimate.interval is None


def test_five_verified_outcomes_produce_a_beta_posterior() -> None:
    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(4)
    ] + [_candidate("yes", outcome=OutcomeResolutionStatus.YES, days_ago=8)]
    estimate = _baseline(candidates)
    assert estimate.status is PredictionStatus.OK
    assert estimate.verified_outcomes == 5
    assert estimate.positive_outcomes == 1
    assert estimate.probability == pytest.approx(2 / 7)
    assert estimate.interval is not None
    assert estimate.interval.lower == pytest.approx(float(beta_dist.ppf(0.05, 2, 5)))
    assert estimate.interval.upper == pytest.approx(float(beta_dist.ppf(0.95, 2, 5)))


def test_the_interval_is_ninety_percent_and_has_no_width_gate() -> None:
    """C20: the old 0.60 width cut was unreachable and was retired."""

    candidates = [
        _candidate(f"yes-{index}", outcome=OutcomeResolutionStatus.YES, days_ago=index + 3)
        for index in range(5)
    ]
    estimate = _baseline(candidates)
    assert estimate.status is PredictionStatus.OK
    assert estimate.interval is not None
    assert estimate.interval.upper - estimate.interval.lower > 0.30


def test_a_conflict_in_scope_blocks_the_estimate() -> None:
    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(5)
    ] + [_candidate("conflicted", outcome=OutcomeResolutionStatus.CONFLICTED, days_ago=10)]
    estimate = _baseline(candidates)
    assert estimate.status is PredictionStatus.ABSTAINED
    assert PredictionAbstentionReason.UNRESOLVED_CONFLICT in estimate.abstention_reasons


def test_a_conflict_outside_the_scope_does_not_block() -> None:
    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(5)
    ] + [
        _candidate(
            "other-mode",
            outcome=OutcomeResolutionStatus.CONFLICTED,
            days_ago=10,
            care_mode="another_mode",
        )
    ]
    assert _baseline(candidates).status is PredictionStatus.OK


def test_an_ever_conflicted_episode_never_counts_even_once_resolved() -> None:
    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(4)
    ] + [
        _candidate(
            "was-conflicted",
            outcome=OutcomeResolutionStatus.NO,
            days_ago=9,
            ever_conflicted=True,
        )
    ]
    estimate = _baseline(candidates)
    assert estimate.verified_outcomes == 4
    assert estimate.status is PredictionStatus.ABSTAINED


def test_a_missing_care_mode_abstains_for_that_reason() -> None:
    estimate = _baseline([], care_mode=None)
    assert estimate.abstention_reasons == (
        PredictionAbstentionReason.CARE_MODE_HISTORY_UNAVAILABLE,
    )


def test_another_target_definition_version_is_a_different_question() -> None:
    candidates = [
        _candidate(
            f"other-{index}",
            outcome=OutcomeResolutionStatus.NO,
            days_ago=index + 3,
            target_version="target-demo-2",
        )
        for index in range(5)
    ]
    assert _baseline(candidates).verified_outcomes == 0


def test_the_window_is_sixty_inclusive_days() -> None:
    inside = [
        _candidate(f"in-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 55)
        for index in range(5)
    ]
    assert _baseline(inside).verified_outcomes == 5
    outside = [
        _candidate(f"out-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 60)
        for index in range(5)
    ]
    assert _baseline(outside).verified_outcomes == 0


def test_an_unauthorised_outcome_is_excluded() -> None:
    candidates = [
        _candidate(
            f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3, consent=False
        )
        for index in range(5)
    ]
    assert _baseline(candidates).verified_outcomes == 0


def test_a_resolution_that_arrived_after_the_cutoff_is_not_yet_known() -> None:
    candidates = [
        _candidate(f"no-{index}", outcome=OutcomeResolutionStatus.NO, days_ago=index + 3)
        for index in range(4)
    ] + [
        _candidate(
            "future",
            outcome=OutcomeResolutionStatus.NO,
            days_ago=1,
            resolved_offset_hours=48,
        )
    ]
    estimate = _baseline(candidates, as_of_at=NOW)
    assert estimate.verified_outcomes == 4


def test_a_pending_or_unknown_resolution_never_becomes_a_negative() -> None:
    candidates = [
        _candidate(f"pending-{index}", outcome=OutcomeResolutionStatus.PENDING, days_ago=index + 3)
        for index in range(5)
    ] + [
        _candidate(f"unknown-{index}", outcome=OutcomeResolutionStatus.UNKNOWN, days_ago=index + 9)
        for index in range(5)
    ]
    assert _baseline(candidates).verified_outcomes == 0


def test_the_baseline_declares_no_band_and_no_decision_policy() -> None:
    estimate = _baseline([])
    assert not hasattr(estimate, "risk_band")
    assert not hasattr(estimate, "decision_policy_version")


# --- challenger -----------------------------------------------------------


def test_the_predictor_encoding_maps_other_and_unknown_to_null() -> None:
    assert encode_predictor(FieldCode.SLEEP_QUALITY, "interrupted") == 1.0
    assert encode_predictor(FieldCode.SLEEP_QUALITY, "sleep_onset_difficulty") == 1.0
    assert encode_predictor(FieldCode.SLEEP_QUALITY, "restorative") == 0.0
    assert encode_predictor(FieldCode.SLEEP_QUALITY, "other") is None
    assert encode_predictor(FieldCode.SLEEP_QUALITY, None) is None
    assert encode_predictor(FieldCode.DAILY_REGULATION_STATE, "stable_with_support") == 0.0
    assert encode_predictor(FieldCode.DAILY_REGULATION_STATE, "frequent_dysregulation") == 1.0


def test_only_the_two_preregistered_predictors_exist() -> None:
    """C23: nothing selects a third predictor from the data."""

    with pytest.raises(ValueError, match="preregistered"):
        encode_predictor(FieldCode.GI_STATUS, "normal")


def test_the_personal_rate_needs_five_days_and_never_mixes_sources() -> None:
    rows = [
        observation(
            f"sleep-{index}",
            field_code=FieldCode.SLEEP_QUALITY,
            value="interrupted" if index % 2 else "restorative",
            effective_at=NOW - timedelta(days=index + 1),
        )
        for index in range(6)
    ]
    rate = personal_predictor_rate(
        rows,
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.SLEEP_QUALITY,
        as_of_at=NOW,
    )
    assert rate.n_days == 6
    assert rate.rate == pytest.approx(0.5)

    thin = personal_predictor_rate(
        rows[:3],
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.SLEEP_QUALITY,
        as_of_at=NOW,
    )
    assert thin.rate is None
    assert thin.reason == "personal_predictor_history_insufficient"


def test_an_other_answer_does_not_count_as_a_zero_in_the_personal_rate() -> None:
    rows = [
        observation(
            f"sleep-{index}",
            field_code=FieldCode.SLEEP_QUALITY,
            value="other",
            effective_at=NOW - timedelta(days=index + 1),
        )
        for index in range(6)
    ]
    rate = personal_predictor_rate(
        rows,
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.SLEEP_QUALITY,
        as_of_at=NOW,
    )
    assert rate.rate is None
    assert rate.n_days == 0


def _rows(labels: list[int], subjects: int = 2) -> list[ChallengerRow]:
    return [
        ChallengerRow(
            subject_id=ident(f"subject-{index % subjects}"),
            p_base=0.2,
            sleep_deviation=0.3 if label else -0.2,
            regulation_deviation=0.1 if label else -0.1,
            label=label,
        )
        for index, label in enumerate(labels)
    ]


def test_a_single_class_is_not_trainable() -> None:
    """INV-19, and the expected result with today's data."""

    report = assess_trainability(_rows([0, 0, 0, 0, 0, 0]))
    assert not report.trainable
    assert report.reason is NotTrainableReason.SINGLE_CLASS

    result = train_challenger(_rows([0, 0, 0, 0, 0, 0]))
    assert result.trainable is False
    assert result.reason is NotTrainableReason.SINGLE_CLASS
    assert result.fit is None


def test_a_training_partition_with_one_class_is_not_trainable() -> None:
    rows = [
        ChallengerRow(
            subject_id=ident("subject-a"),
            p_base=0.2,
            sleep_deviation=0.3,
            regulation_deviation=0.1,
            label=1,
        ),
        ChallengerRow(
            subject_id=ident("subject-b"),
            p_base=0.2,
            sleep_deviation=-0.2,
            regulation_deviation=-0.1,
            label=0,
        ),
    ]
    report = assess_trainability(rows)
    assert not report.trainable
    assert report.reason is NotTrainableReason.SINGLE_CLASS


def test_one_subject_cannot_support_leave_one_group_out() -> None:
    rows = _rows([0, 1, 0, 1], subjects=1)
    report = assess_trainability(rows)
    assert report.reason is NotTrainableReason.INSUFFICIENT_SAMPLE_PLAN


def test_the_objective_is_the_literal_spec_formula() -> None:
    rows = _rows([0, 1, 0, 1])
    coefficients = [0.1, 0.2, -0.3]
    expected = 0.0
    for row in rows:
        eta = (
            logit(row.p_base)
            + coefficients[0]
            + coefficients[1] * row.sleep_deviation
            + coefficients[2] * row.regulation_deviation
        )
        probability = sigmoid(eta)
        expected -= row.label * __import__("math").log(probability) + (1 - row.label) * (
            __import__("math").log(1 - probability)
        )
    expected = expected / len(rows) + 1.0 / 2.0 * (0.2**2 + (-0.3) ** 2)
    assert negative_log_likelihood(coefficients, rows, 1.0) == pytest.approx(expected)


def test_the_intercept_is_not_penalised() -> None:
    rows = _rows([0, 1, 0, 1])
    with_intercept = negative_log_likelihood([5.0, 0.0, 0.0], rows, 100.0)
    without_penalty = negative_log_likelihood([5.0, 0.0, 0.0], rows, 0.0)
    assert with_intercept == pytest.approx(without_penalty)


def test_the_baseline_offset_carries_a_fixed_coefficient_of_one() -> None:
    row = ChallengerRow(
        subject_id=ident("subject-a"),
        p_base=0.2,
        sleep_deviation=0.0,
        regulation_deviation=0.0,
        label=1,
    )
    fit = fit_challenger([row], penalty=0.0)
    assert fit.converged
    predicted = fit.predict(row)
    assert predicted is not None
    assert predicted > 0.2


def test_a_tie_within_tolerance_chooses_the_larger_penalty() -> None:
    """C44: equal Brier picks more regularisation."""

    rows = _rows([0, 1, 0, 1, 1, 0, 1, 0])
    selection = select_penalty(rows)
    assert selection.penalty in CHALLENGER_L2_GRID
    briers = [brier for _, brier in selection.scores if brier is not None]
    best = min(briers)
    tied = [
        penalty
        for penalty, brier in selection.scores
        if brier is not None and brier - best <= 1e-12
    ]
    assert selection.penalty == max(tied)


def test_a_trainable_dataset_produces_a_candidate_and_nothing_more() -> None:
    result = train_challenger(_rows([0, 1, 0, 1, 1, 0, 1, 0]))
    assert result.trainable
    assert result.fit is not None and result.fit.converged
    assert result.model_version == "real-logit-challenger-0.3.0"
    assert not hasattr(result, "deployed")
