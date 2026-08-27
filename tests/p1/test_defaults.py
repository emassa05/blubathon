"""Smart defaults: golden vectors, the clean window and the presentation rule.

The golden numbers come from the corrected table in FUNDAMENTOS 5.4 and the
Dirichlet worked example in FUNDAMENTOS 6.1. They are checked against SciPy, not
against a hand-written approximation.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from scipy.stats import beta as beta_dist

from ml.defaults import (
    DefaultStatus,
    Stratum,
    assign_audit_mode,
    compute_binary_default,
    compute_categorical_default,
    compute_default_decision,
    eligible_history,
)
from ml.spec_constants import (
    AUDIT_BUCKET_MODULUS,
    AUDIT_BUCKET_THRESHOLD,
    DEFAULT_LOWER_QUANTILE,
    DEFAULT_LOWER_THRESHOLD,
)
from packages.shared.canonical import local_date
from packages.shared.enums import DataOrigin, EntryMode, FieldCode, Source
from packages.shared.field_catalog import closed_support
from tests.p1.factories import NOW, SUBJECT, TENANT, ident, observation

SECRET = b"fixed-test-secret"
STRATUM = Stratum(
    tenant_id=TENANT, subject_id=SUBJECT, source=Source.HOME, field_code=FieldCode.FOOD_CHANGES
)

# FUNDAMENTOS 5.4, the corrected table.
GOLDEN_BINARY = (
    (2, 0, 3, 1, 0.7500, 0.3684, False),
    (8, 2, 9, 3, 0.7500, 0.5299, False),
    (32, 8, 33, 9, 0.7857, 0.6754, False),
    (80, 20, 81, 21, 0.7941, 0.7254, True),
)


@pytest.mark.parametrize(
    ("hits", "misses", "alpha", "beta", "mean", "lower", "passes"), GOLDEN_BINARY
)
def test_binary_golden_vectors_match_fundamentos(
    hits: int, misses: int, alpha: int, beta: int, mean: float, lower: float, passes: bool
) -> None:
    estimate = compute_binary_default(true_count=hits, false_count=misses)
    assert (estimate.alpha, estimate.posterior_beta) == (alpha, beta)
    assert estimate.posterior_mean == pytest.approx(mean, abs=5e-5)
    assert estimate.lower_bound == pytest.approx(lower, abs=5e-5)
    assert (estimate.lower_bound > DEFAULT_LOWER_THRESHOLD) is passes


def test_the_lower_bound_comes_from_scipy() -> None:
    estimate = compute_binary_default(true_count=32, false_count=8)
    assert estimate.lower_bound == pytest.approx(
        float(beta_dist.ppf(DEFAULT_LOWER_QUANTILE, 33, 9))
    )


def test_two_of_two_is_not_the_clopper_pearson_bound() -> None:
    """FUNDAMENTOS 5.4: 22.36% answers a different, frequentist question."""

    estimate = compute_binary_default(true_count=2, false_count=0)
    assert estimate.lower_bound == pytest.approx(0.3684, abs=5e-5)
    assert estimate.lower_bound != pytest.approx(0.2236, abs=1e-3)


def test_a_binary_tie_produces_no_candidate() -> None:
    estimate = compute_binary_default(true_count=5, false_count=5)
    assert estimate.tie
    assert estimate.candidate is None
    assert not estimate.has_candidate


def test_the_candidate_is_the_more_frequent_value() -> None:
    assert compute_binary_default(true_count=7, false_count=3).candidate is True
    assert compute_binary_default(true_count=3, false_count=7).candidate is False


def test_dirichlet_worked_example_from_fundamentos() -> None:
    """counts [1,2,3,32,2] over a 1-5 scale gives the candidate a Beta(33,12)."""

    estimate = compute_categorical_default(
        counts={1: 1, 2: 2, 3: 3, 4: 32, 5: 2}, support=(1, 2, 3, 4, 5)
    )
    assert estimate.candidate == 4
    assert (estimate.alpha, estimate.posterior_beta) == (33, 12)
    assert estimate.n_observations == 40
    assert estimate.lower_bound == pytest.approx(float(beta_dist.ppf(0.05, 33, 12)))


def test_an_unobserved_category_still_holds_prior_mass() -> None:
    estimate = compute_categorical_default(
        counts={"normal": 10}, support=closed_support(FieldCode.GI_STATUS)
    )
    assert estimate.alpha == 11
    assert estimate.posterior_beta == 3  # three unobserved categories, prior 1 each


def test_a_categorical_tie_produces_no_candidate() -> None:
    estimate = compute_categorical_default(counts={1: 4, 2: 4}, support=(1, 2, 3, 4, 5))
    assert estimate.tie
    assert estimate.candidate is None


def test_counts_outside_the_support_are_a_contract_error() -> None:
    with pytest.raises(ValueError, match="outside the support"):
        compute_categorical_default(counts={"reparador": 3}, support=("restorative", "other"))


def test_the_binary_case_is_the_two_category_marginal() -> None:
    binary = compute_binary_default(true_count=8, false_count=2)
    categorical = compute_categorical_default(counts={True: 8, False: 2}, support=(False, True))
    assert (binary.alpha, binary.posterior_beta) == (
        categorical.alpha,
        categorical.posterior_beta,
    )
    assert binary.lower_bound == pytest.approx(categorical.lower_bound)


# --- the clean window -----------------------------------------------------


def _history(rows: list, *, cutoff=NOW, stratum: Stratum = STRATUM):
    return eligible_history(rows, stratum=stratum, cutoff=cutoff)


def _daily(label: str, day_offset: int, **overrides):
    return observation(label, effective_at=NOW - timedelta(days=day_offset), **overrides)


def test_only_the_eligible_entry_modes_count() -> None:
    rows = [
        _daily("manual", 1, entry_mode=EntryMode.MANUAL_NO_DEFAULT, value=False),
        _daily("audit", 2, entry_mode=EntryMode.AUDIT_MANUAL, value=False),
        _daily("accepted", 3, entry_mode=EntryMode.DEFAULT_ACCEPTED, value=False),
        _daily("edited", 4, entry_mode=EntryMode.DEFAULT_EDITED, value=True),
        _daily("unknown", 5, entry_mode=EntryMode.EXPLICIT_UNKNOWN, value=None),
    ]
    history = _history(rows)
    assert history.n_observations == 2
    assert {row.entry_mode for row in history.observations} == {
        EntryMode.MANUAL_NO_DEFAULT,
        EntryMode.AUDIT_MANUAL,
    }


def test_an_accepted_suggestion_never_moves_the_posterior() -> None:
    """INV-02: accepting a default must not make the next default more confident."""

    manual = [_daily(f"manual-{index}", index + 1, value=False) for index in range(10)]
    before = compute_default_decision(_history(manual), audit_mode=False)
    accepted = [
        _daily(f"accepted-{index}", index + 20, entry_mode=EntryMode.DEFAULT_ACCEPTED, value=False)
        for index in range(30)
    ]
    after = compute_default_decision(_history(manual + accepted), audit_mode=False)
    assert before.estimate is not None and after.estimate is not None
    assert after.estimate.lower_bound == before.estimate.lower_bound
    assert after.estimate.n_observations == before.estimate.n_observations


def test_an_edited_default_also_stays_out_of_the_estimator() -> None:
    """INV-03: an edited suggestion describes the day but was still anchored."""

    manual = [_daily(f"manual-{index}", index + 1, value=False) for index in range(4)]
    edited = [
        _daily(f"edited-{index}", index + 10, entry_mode=EntryMode.DEFAULT_EDITED, value=False)
        for index in range(20)
    ]
    assert _history(manual + edited).n_observations == 4


def test_synthetic_rows_never_inform_a_real_default() -> None:
    rows = [
        _daily("real", 1, value=False),
        _daily("synthetic", 2, value=False, data_origin=DataOrigin.SYNTHETIC),
    ]
    assert _history(rows).n_observations == 1


def test_an_import_counts_only_with_an_approved_mapping() -> None:
    approved = ident("approved-mapping")
    rows = [
        _daily(
            "approved",
            1,
            entry_mode=EntryMode.IMPORTED_OBSERVED,
            value=False,
            source_mapping_id=approved,
        ),
        _daily(
            "unapproved",
            2,
            entry_mode=EntryMode.IMPORTED_OBSERVED,
            value=False,
            source_mapping_id=ident("other-mapping"),
        ),
    ]
    history = eligible_history(
        rows, stratum=STRATUM, cutoff=NOW, approved_mapping_ids=frozenset({approved})
    )
    assert history.n_observations == 1


def test_the_window_is_sixty_inclusive_days() -> None:
    inside = _daily("inside", 59, value=False)
    outside = _daily("outside", 60, value=False)
    history = _history([inside, outside])
    assert [row.field_observation_id for row in history.observations] == [
        inside.field_observation_id
    ]


def test_history_never_crosses_a_stratum() -> None:
    other_subject = _daily("other-subject", 1, value=False, subject_id=ident("other-subject"))
    other_tenant = _daily("other-tenant", 2, value=False, tenant_id=ident("other-tenant"))
    same = _daily("same", 3, value=False)
    assert _history([other_subject, other_tenant, same]).n_observations == 1


def test_a_correction_after_the_cutoff_does_not_change_a_past_suggestion() -> None:
    """INV-11: a snapshot emitted today is not rewritten by tomorrow's correction."""

    original = _daily("original", 1, value=False)
    correction = observation(
        "correction",
        effective_at=original.effective_at,
        ingested_at=NOW + timedelta(days=1),
        value=True,
        supersedes_id=original.field_observation_id,
    )
    at_cutoff = _history([original, correction])
    assert [row.value for row in at_cutoff.observations] == [False]
    later = _history([original, correction], cutoff=NOW + timedelta(days=1))
    assert [row.value for row in later.observations] == [True]


def test_two_active_leaves_on_one_day_suppress_the_suggestion() -> None:
    rows = [
        _daily("first", 1, value=False),
        _daily("second", 1, value=True),
    ]
    history = _history(rows)
    assert not history.is_clean
    assert history.n_observations == 0
    decision = compute_default_decision(history, audit_mode=False)
    assert decision.status is DefaultStatus.SUPPRESSED_CONFLICT


# --- the presentation rule ------------------------------------------------


def test_a_strong_history_presents_a_suggestion() -> None:
    rows = [_daily(f"row-{index}", index + 1, value=False) for index in range(50)]
    decision = compute_default_decision(_history(rows), audit_mode=False)
    assert decision.status is DefaultStatus.PRESENTED
    contract = decision.to_contract()
    assert contract is not None
    assert contract.candidate_value is False
    assert contract.lower_bound > DEFAULT_LOWER_THRESHOLD
    assert contract.quantile == DEFAULT_LOWER_QUANTILE


def test_the_cut_is_strict_so_exactly_the_threshold_is_not_enough() -> None:
    """INV-07: `lower = 0.70` shows nothing."""

    from ml.defaults.estimator import DefaultDecision, PosteriorEstimate

    at_threshold = PosteriorEstimate(
        candidate=False,
        candidate_count=1,
        n_observations=1,
        alpha=1.0,
        posterior_beta=1.0,
        posterior_mean=0.5,
        lower_bound=DEFAULT_LOWER_THRESHOLD,
        tie=False,
    )
    assert not at_threshold.lower_bound > DEFAULT_LOWER_THRESHOLD
    assert (
        DefaultDecision(
            field_code=FieldCode.FOOD_CHANGES,
            status=DefaultStatus.SUPPRESSED_BELOW_THRESHOLD,
            estimate=at_threshold,
        ).to_contract()
        is None
    )


def test_an_audited_session_suppresses_every_suggestion() -> None:
    """INV-04: an audited session returns no defaults, however strong the history."""

    rows = [_daily(f"row-{index}", index + 1, value=False) for index in range(50)]
    decision = compute_default_decision(_history(rows), audit_mode=True)
    assert decision.status is DefaultStatus.SUPPRESSED_AUDIT_MODE
    assert decision.to_contract() is None


def test_a_field_outside_the_allowlist_never_gets_a_suggestion() -> None:
    stratum = Stratum(
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.SLEEP_QUALITY,
    )
    rows = [
        _daily(
            f"row-{index}",
            index + 1,
            field_code=FieldCode.SLEEP_QUALITY,
            value="restorative",
        )
        for index in range(50)
    ]
    decision = compute_default_decision(_history(rows, stratum=stratum), audit_mode=False)
    assert decision.status is DefaultStatus.SUPPRESSED_NOT_ALLOWLISTED


def test_a_posterior_tie_returns_no_suggestion() -> None:
    """INV-06: a tie means `default = null`, not an arbitrary winner."""

    rows = [_daily(f"true-{index}", index + 1, value=True) for index in range(5)]
    rows += [_daily(f"false-{index}", index + 20, value=False) for index in range(5)]
    decision = compute_default_decision(_history(rows), audit_mode=False)
    assert decision.status is DefaultStatus.SUPPRESSED_TIE
    assert decision.to_contract() is None


def test_an_empty_history_says_so_instead_of_guessing() -> None:
    decision = compute_default_decision(_history([]), audit_mode=False)
    assert decision.status is DefaultStatus.SUPPRESSED_NO_ELIGIBLE_HISTORY


def test_an_ordinal_field_keeps_its_categories() -> None:
    stratum = Stratum(
        tenant_id=TENANT,
        subject_id=SUBJECT,
        source=Source.HOME,
        field_code=FieldCode.ACTIVITY_PARTICIPATION,
    )
    rows = [
        _daily(
            f"row-{index}",
            index + 1,
            field_code=FieldCode.ACTIVITY_PARTICIPATION,
            value=4,
        )
        for index in range(50)
    ]
    decision = compute_default_decision(_history(rows, stratum=stratum), audit_mode=False)
    assert decision.status is DefaultStatus.PRESENTED
    contract = decision.to_contract()
    assert contract is not None
    assert contract.candidate_value == 4


# --- audit assignment -----------------------------------------------------


def _assign(**overrides):
    payload = {
        "secret": SECRET,
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "local_date": local_date(NOW),
        "policy_version": "form-0.3.0",
    }
    payload.update(overrides)
    return assign_audit_mode(**payload)


def test_the_assignment_is_stable_for_the_same_inputs() -> None:
    """INV-05: reopening a session does not change `audit_mode`."""

    first = _assign()
    assert first == _assign()
    assert 0 <= first.bucket < AUDIT_BUCKET_MODULUS
    assert first.audit_mode is (first.bucket < AUDIT_BUCKET_THRESHOLD)


def test_a_different_day_subject_or_policy_is_a_different_assignment() -> None:
    base = _assign().bucket
    assert _assign(local_date=local_date(NOW) + timedelta(days=1)).bucket != base
    assert _assign(subject_id=ident("another-subject")).bucket != base
    assert _assign(policy_version="form-0.3.1").bucket != base


def test_the_client_cannot_predict_the_bucket_without_the_secret() -> None:
    assert _assign(secret=b"another-secret").bucket != _assign().bucket


def test_the_audit_rate_is_ten_percent_of_the_bucket_space() -> None:
    assert AUDIT_BUCKET_THRESHOLD == 100
    assert AUDIT_BUCKET_MODULUS == 1000


def test_the_assignment_is_roughly_the_declared_rate() -> None:
    audited = sum(
        1 for index in range(2000) if _assign(subject_id=ident(f"subject-{index}")).audit_mode
    )
    assert 0.07 < audited / 2000 < 0.13
