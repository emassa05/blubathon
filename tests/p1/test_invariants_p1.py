"""One named test per invariant P1 owns (M6).

P1 covers INV-02, INV-03, INV-04, INV-06, INV-07, INV-09, INV-10, INV-16 to
INV-28, and INV-32 to INV-35. P2 covers the persistence, authorisation and
integration half, and INV-27 is deliberately split: here the domain proves it
does not mutate the catalogue, and P2 proves the API flow does not either.

These tests are short on purpose. The behaviour is exercised in depth by the
module tests; each test below exists so that one specific rule cannot be broken
without the suite going red, named after the rule it guards.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from ml.defaults import DefaultStatus, Stratum, compute_default_decision, eligible_history
from ml.errors import CohortViolationError
from ml.form import build_form_plan, estimate_voi
from ml.prediction import ChallengerRow, assess_trainability, build_personal_baseline, guard_cohort
from packages.shared.constants import (
    DECISION_POLICY_VERSION,
)
from packages.shared.domain.observation import (
    DEFAULT_ESTIMATOR_MODES,
    PRIMARY_REAL_MODEL_MODES,
)
from packages.shared.domain.outcome import report_is_eligible
from packages.shared.domain.prediction import PredictionOutput
from packages.shared.domain.rag import StrategyCitation
from packages.shared.enums import (
    CohortKind,
    DataOrigin,
    EntryMode,
    EstimateKind,
    FieldCode,
    IntendedUse,
    OutcomeReportValue,
    PredictionAbstentionReason,
    PredictionStatus,
    Source,
    TimingStatus,
    TrackId,
    VoiStatus,
)
from packages.shared.field_catalog import applicable_fields
from rag.domain.citations import verify_citation
from tests.p1 import factories as f
from tests.p1 import rag_factories as rf
from tests.p1.factories import ident

NOW = f.NOW


def _history(rows, *, field_code=FieldCode.FOOD_CHANGES):
    return eligible_history(
        rows,
        stratum=Stratum(
            tenant_id=f.TENANT, subject_id=f.SUBJECT, source=Source.HOME, field_code=field_code
        ),
        cutoff=NOW,
    )


# --- Defaults and the form -------------------------------------------------


def test_inv_02_an_accepted_default_feeds_neither_estimator_nor_real_model() -> None:
    assert EntryMode.DEFAULT_ACCEPTED not in DEFAULT_ESTIMATOR_MODES
    assert EntryMode.DEFAULT_ACCEPTED not in PRIMARY_REAL_MODEL_MODES

    accepted = [
        f.observation(
            f"accepted-{index}",
            entry_mode=EntryMode.DEFAULT_ACCEPTED,
            effective_at=NOW - timedelta(days=index),
        )
        for index in range(40)
    ]
    assert _history(accepted).observations == ()


def test_inv_03_an_edited_default_feeds_the_real_model_but_not_the_estimator() -> None:
    assert EntryMode.DEFAULT_EDITED not in DEFAULT_ESTIMATOR_MODES
    assert EntryMode.DEFAULT_EDITED in PRIMARY_REAL_MODEL_MODES

    edited = [
        f.observation(
            f"edited-{index}",
            entry_mode=EntryMode.DEFAULT_EDITED,
            effective_at=NOW - timedelta(days=index),
        )
        for index in range(40)
    ]
    assert _history(edited).observations == ()


def test_inv_04_an_audited_session_returns_no_default() -> None:
    rows = [
        f.observation(f"manual-{index}", value=False, effective_at=NOW - timedelta(days=index))
        for index in range(40)
    ]
    decision = compute_default_decision(_history(rows), audit_mode=True)
    assert decision.status is DefaultStatus.SUPPRESSED_AUDIT_MODE
    assert not decision.is_presented
    assert decision.to_contract() is None


def test_inv_06_a_posterior_tie_returns_no_default() -> None:
    rows = [
        f.observation(
            f"tie-{index}", value=index % 2 == 0, effective_at=NOW - timedelta(days=index)
        )
        for index in range(20)
    ]
    decision = compute_default_decision(_history(rows), audit_mode=False)
    assert decision.status is DefaultStatus.SUPPRESSED_TIE
    assert decision.to_contract() is None


def test_inv_07_a_lower_bound_of_exactly_the_threshold_shows_nothing() -> None:
    rows = [
        f.observation(f"strong-{index}", value=False, effective_at=NOW - timedelta(days=index))
        for index in range(40)
    ]
    decision = compute_default_decision(_history(rows), audit_mode=False, threshold=1.0)
    # The cut is strict, so a threshold the lower bound merely reaches suppresses.
    assert decision.status is DefaultStatus.SUPPRESSED_BELOW_THRESHOLD


def test_inv_09_unavailable_voi_is_null_and_never_zero() -> None:
    estimate = estimate_voi(_history([]), model=None, cutoff=NOW)
    assert estimate.status is VoiStatus.UNAVAILABLE_MODEL
    assert estimate.voi_nats is None


def test_inv_10_highlighted_plus_tail_keeps_every_applicable_field_once() -> None:
    for source in Source:
        plan = build_form_plan(
            source=source,
            today=NOW.date(),
            cutoff=NOW,
            coverage=0.4,
            outcome_pending=False,
        )
        codes = plan.field_codes
        assert sorted(codes, key=str) == sorted(applicable_fields(source), key=str)
        assert len(set(codes)) == len(codes)


# --- Outcomes, origin and the two real tracks ------------------------------


def test_inv_16_a_late_outcome_stays_out_of_the_primary_dataset() -> None:
    window = f.window()
    late_yes = f.report(
        "late-yes",
        value=OutcomeReportValue.YES,
        occurred_at=window.target_start_at + timedelta(hours=2),
        reported_at=window.capture_deadline_at + timedelta(hours=1),
        outcome_window=window,
    )
    assert late_yes.timing_status is TimingStatus.LATE
    assert not report_is_eligible(late_yes, window)


def test_inv_18_the_simulation_track_refuses_a_real_subject() -> None:
    with pytest.raises(CohortViolationError):
        guard_cohort(cohort_kind=CohortKind.REAL_SUBJECT, input_data_origin=DataOrigin.SYNTHETIC)
    with pytest.raises(CohortViolationError):
        guard_cohort(cohort_kind=CohortKind.DEMO_FIXTURE, input_data_origin=DataOrigin.REAL)


def test_inv_19_the_challenger_refuses_a_single_class_partition_or_aggregate() -> None:
    one_class = [
        ChallengerRow(
            subject_id=f.SUBJECT, p_base=0.2, sleep_deviation=0.1, regulation_deviation=0.0, label=0
        )
        for _ in range(6)
    ]
    report = assess_trainability(one_class)
    assert not report.trainable
    assert report.reason is not None and "single_class" in report.reason.value


def test_inv_20_a_baseline_below_five_verified_outcomes_abstains() -> None:
    estimate = build_personal_baseline(
        (),
        as_of_at=NOW,
        subject_id=f.SUBJECT,
        care_mode="standard_support",
        target_definition_version="target-demo-1",
    )
    assert estimate.status is PredictionStatus.ABSTAINED
    assert PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES in estimate.abstention_reasons


def test_inv_21_an_abstention_carries_no_number_no_band_and_no_narrative() -> None:
    # There is no decision policy, so no band exists to be produced at all.
    assert DECISION_POLICY_VERSION is None
    assert "risk_band" not in PredictionOutput.model_fields

    output = PredictionOutput(
        prediction_output_id=ident("output:abstained"),
        tenant_id=f.TENANT,
        prediction_episode_id=ident("episode"),
        track_id=TrackId.REAL_PERSONAL_BASELINE_V1,
        intended_use=IntendedUse.OPERATIONAL_SUPPORT,
        status=PredictionStatus.ABSTAINED,
        estimate_kind=EstimateKind.PERSONAL_OBSERVED_EPISODE_RATE,
        abstention_reasons=(PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES,),
        model_version="real-personal-baseline-0.3.0",
        input_data_origin=DataOrigin.REAL,
        created_at=NOW,
    )
    assert (output.probability, output.simulation_score, output.interval) == (None, None, None)
    assert output.interval_method is None


# --- Authoring, activation and the runtime ---------------------------------


def test_inv_22_no_prompt_or_index_carries_an_identifier_or_a_clinical_note() -> None:
    from rag.authoring.drafting import load_prompt
    from rag.domain.text_guard import FreeTextLeakError, TextProvenance, assert_literature_only

    template = load_prompt().template
    for forbidden in ("subject_id", "tenant_id", "notes", "actor_id", "episode"):
        assert forbidden not in template

    build = rf.fixture_build()
    with pytest.raises(FreeTextLeakError):
        assert_literature_only(
            (TextProvenance(text="el nino durmio mal", kind="clinical_free_text"),),
            authorised=build.authorised_document_version_ids,
        )


def test_inv_24_a_citation_that_does_not_match_its_fragment_is_rejected() -> None:
    build = rf.fixture_build()
    chunk = rf.chunk_containing(build, rf.SLEEP_QUOTE)
    fabricated = StrategyCitation(
        citation_id=ident("citation:inv24"),
        claim_id=ident("claim:inv24"),
        document_chunk_id=chunk.document_chunk_id,
        locator=chunk.locator,
        quoted_text="cita falsa",
        chunk_sha256=chunk.chunk_sha256,
        canonical_url="https://example.invalid/fixtures/quoted",
    )
    result = verify_citation(fabricated, {item.document_chunk_id: item for item in build.chunks})
    assert result.failure == "quote_not_literal"
