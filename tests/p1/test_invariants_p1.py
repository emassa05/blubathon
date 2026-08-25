"""One named test per SPEC 17 invariant P1 owns (TAREAS M6).

P1 covers INV-02, INV-03, INV-04, INV-06, INV-07, INV-09, INV-10, INV-16 to
INV-28, and INV-32 to INV-35. P2 covers the persistence, authorisation and
integration half, and INV-27 is deliberately split: here the domain proves it
does not mutate the catalogue, and P2 proves the API flow does not either.

These tests are short on purpose. The behaviour is exercised in depth by the
module tests; each test below exists so that one specific rule cannot be broken
without the suite going red, named after the rule it guards (CONVENTIONS 16).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ml.defaults import DefaultStatus, Stratum, compute_default_decision, eligible_history
from ml.errors import CohortViolationError, OriginMixError, UnmappedSourceValueError
from ml.eval.metrics import auc_roc, average_precision
from ml.eval.protocol import EVALUATION_PROTOCOL_VERSION, nested_out_of_fold
from ml.eval.report import build_evaluation_report
from ml.form import build_form_plan, estimate_voi
from ml.prediction import ChallengerRow, assess_trainability, build_personal_baseline, guard_cohort
from packages.shared.constants import (
    DECISION_POLICY_VERSION,
    PRODUCTION_ACCEPTANCE_RERANK_WEIGHT,
    RUNTIME_LLM_CALLS,
    STRATEGY_REQUIRED_DISTINCT_REVIEWERS,
)
from packages.shared.domain.observation import (
    DEFAULT_ESTIMATOR_MODES,
    PRIMARY_REAL_MODEL_MODES,
)
from packages.shared.domain.outcome import report_is_eligible
from packages.shared.domain.prediction import PredictionOutput
from packages.shared.domain.rag import ScenarioPredicate
from packages.shared.enums import (
    AuthoringReviewKind,
    AuthoringReviewObjectType,
    CohortKind,
    DataOrigin,
    DocumentStatus,
    EntryMode,
    EstimateKind,
    FieldCode,
    IntendedUse,
    MetricStatus,
    OutcomeReportValue,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
    RecommendationAbstentionReason,
    RuntimeStatus,
    Source,
    StrategyStatus,
    TimingStatus,
    TrackId,
    VoiStatus,
)
from packages.shared.field_catalog import applicable_fields
from rag.domain.activation import strategy_activation_decision, suspended_by_dependency
from rag.domain.reviews import ReviewLedger
from rag.runtime import RuntimeCatalog, RuntimeInputs, decide
from tests.p1 import factories as f
from tests.p1 import rag_factories as rf
from tests.p1 import train_factories as tf
from tests.p1.factories import ident
from tests.p1.test_rag_domain import CLINICAL, EVIDENCE, _reviewed_strategy
from tests.p1.test_train import CUTOFF, SUBJECT_A, _build, _single_class_inputs, _two_class_inputs
from tools.train.run import run_challenger_training
from tools.train.snapshot import SnapshotInputs

NOW = f.NOW


def _history(rows, *, field_code=FieldCode.FOOD_CHANGES):
    return eligible_history(
        rows,
        stratum=Stratum(
            tenant_id=f.TENANT, subject_id=f.SUBJECT, source=Source.HOME, field_code=field_code
        ),
        cutoff=NOW,
    )


def _ledger(reviews, actors):
    return ReviewLedger(reviews, actors, cutoff=rf.NOW)


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


def test_inv_17_a_synthetic_row_fails_a_real_snapshot() -> None:
    inputs = _single_class_inputs()
    synthetic = tf.episode(
        "synthetic-inv17",
        subject_id=SUBJECT_A,
        prediction_at=CUTOFF - timedelta(days=1),
        data_origin=DataOrigin.SYNTHETIC,
        cohort_kind=CohortKind.DEMO_FIXTURE,
    )
    with pytest.raises(OriginMixError):
        _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=DataOrigin.REAL,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=(*inputs.episodes, synthetic),
                resolutions=inputs.resolutions,
                observations=inputs.observations,
                consents=inputs.consents,
            )
        )


def test_inv_18_the_simulation_track_refuses_a_real_subject() -> None:
    with pytest.raises(CohortViolationError):
        guard_cohort(cohort_kind=CohortKind.REAL_SUBJECT, input_data_origin=DataOrigin.SYNTHETIC)
    with pytest.raises(CohortViolationError):
        guard_cohort(cohort_kind=CohortKind.DEMO_FIXTURE, input_data_origin=DataOrigin.REAL)


def test_inv_19_the_challenger_refuses_a_single_class_partition_or_aggregate() -> None:
    one_class = [
        ChallengerRow(
            subject_id=SUBJECT_A, p_base=0.2, sleep_deviation=0.1, regulation_deviation=0.0, label=0
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


def test_inv_23_a_strategy_without_a_cited_claim_cannot_activate() -> None:
    build = rf.fixture_build()
    strategy, reviews, actors = _reviewed_strategy(build)
    uncited = strategy.model_copy(update={"citations": ()})
    decision = strategy_activation_decision(
        uncited,
        chunks=build.chunks,
        documents=build.documents,
        ledger=_ledger(reviews, actors),
    )
    assert not decision.approved
    assert "claims_or_citations_empty" in decision.blockers
    assert "claim_without_citation" in decision.blockers


def test_inv_24_a_citation_that_does_not_match_its_fragment_blocks_activation() -> None:
    build = rf.fixture_build()
    strategy, reviews, actors = _reviewed_strategy(build)
    fabricated = strategy.model_copy(
        update={
            "citations": (strategy.citations[0].model_copy(update={"quoted_text": "cita falsa"}),)
        }
    )
    decision = strategy_activation_decision(
        fabricated,
        chunks=build.chunks,
        documents=build.documents,
        ledger=_ledger(reviews, actors),
    )
    assert "citation_not_verified" in decision.blockers


def test_inv_25_one_person_cannot_perform_both_reviews() -> None:
    assert STRATEGY_REQUIRED_DISTINCT_REVIEWERS == 2

    build = rf.fixture_build()
    strategy, reviews, _ = _reviewed_strategy(build)
    same_actor = ident("actor:evidence-reviewer")
    clinical = reviews[1].model_copy(
        update={
            "actor_id": same_actor,
            "accreditation_id": ident("accreditation:evidence-reviewer"),
        }
    )
    accreditation = rf.accreditation("evidence-reviewer", capabilities=EVIDENCE | CLINICAL)
    decision = strategy_activation_decision(
        strategy,
        chunks=build.chunks,
        documents=build.documents,
        ledger=_ledger((reviews[0], clinical), (accreditation,)),
    )
    assert "reviewers_not_distinct" in decision.blockers


def test_inv_26_the_runtime_returns_a_pure_decision_without_llm_or_store() -> None:
    assert RUNTIME_LLM_CALLS == 0

    decision = decide(
        RuntimeInputs(
            scenario=rf.scenario(sleep_quality="interrupted"),
            scenario_hash="fixture-scenario-hash",
            as_of_at=rf.NOW,
            readiness=RecommendationAbstentionReason.CORPUS_NOT_READY,
        )
    )
    assert decision.status is RuntimeStatus.ABSTAINED
    assert decision.authoring_request_intent is not None

    import rag.runtime as runtime_package

    assert not hasattr(runtime_package, "Bm25Index")


def test_inv_27_the_domain_never_mutates_the_active_catalogue() -> None:
    # Acceptance never re-ranks production in v0.3.
    assert PRODUCTION_ACCEPTANCE_RERANK_WEIGHT == 0

    build = rf.fixture_build()
    strategy = rf.strategy(
        "inv27",
        build=build,
        quote=rf.SLEEP_QUOTE,
        action_text=rf.ACTION_TEXT_SLEEP,
        claim_text=rf.CLAIM_TEXT_SLEEP,
        predicate=ScenarioPredicate(),
        evidence_review_id=ident("review:e"),
        clinical_review_id=ident("review:c"),
    )
    version = rf.recommendation_set(
        "inv27",
        strategy_version_ids=(strategy.strategy_version_id,),
        predicate=ScenarioPredicate(),
        clinical_review_id=ident("review:set"),
    )
    catalog = rf.catalog(
        "inv27",
        build=build,
        set_ids=(version.recommendation_set_id,),
        activation_review_id=ident("review:activation"),
    )
    before = catalog.model_dump(mode="json")
    inputs = RuntimeInputs(
        scenario=rf.scenario(sleep_quality="interrupted"),
        scenario_hash="fixture-scenario-hash",
        as_of_at=rf.NOW,
        catalog=RuntimeCatalog(
            catalog=catalog,
            sets=(version,),
            strategies={strategy.strategy_version_id: strategy},
        ),
    )
    decide(inputs)
    decide(inputs)
    assert catalog.model_dump(mode="json") == before
    assert version.status is not StrategyStatus.SUSPENDED


def test_inv_28_a_retired_source_suspends_its_dependants() -> None:
    build = rf.fixture_build()
    strategy, reviews, actors = _reviewed_strategy(build)
    withdrawn = tuple(
        document.model_copy(update={"status": DocumentStatus.WITHDRAWN})
        for document in build.documents
    )
    assert suspended_by_dependency(
        strategy,
        chunks={chunk.document_chunk_id: chunk for chunk in build.chunks},
        documents={document.document_version_id: document for document in withdrawn},
    )
    decision = strategy_activation_decision(
        strategy, chunks=build.chunks, documents=withdrawn, ledger=_ledger(reviews, actors)
    )
    assert "source_retired" in decision.blockers
    # The historical version is still readable; it is simply not activatable.
    assert strategy.action_text_es == rf.ACTION_TEXT_SLEEP


# --- Evaluation ------------------------------------------------------------


def test_inv_32_a_real_evaluation_separates_versions_and_excludes_what_it_must() -> None:
    inputs = _single_class_inputs()

    # One exact target definition version per dataset.
    other, other_resolution = (
        tf.episode(
            "inv32-other",
            subject_id=SUBJECT_A,
            prediction_at=CUTOFF - timedelta(days=3),
            target_definition_version="target-demo-2",
        ),
        None,
    )
    other_resolution = tf.resolution(
        "inv32-other",
        episode_id=other.prediction_episode_id,
        status=OutcomeResolutionStatus.NO,
        resolved_at=CUTOFF - timedelta(days=2),
    )
    build = _build(
        SnapshotInputs(
            tenant_id=inputs.tenant_id,
            data_origin=inputs.data_origin,
            target_definition_version=inputs.target_definition_version,
            cutoff_at=inputs.cutoff_at,
            episodes=(*inputs.episodes, other),
            resolutions=(*inputs.resolutions, other_resolution),
            observations=inputs.observations,
            consents=inputs.consents,
        )
    )
    assert (other.prediction_episode_id, "other_target_definition_version") in build.excluded

    # Consent is re-checked at the run, not trusted from the snapshot.
    outcome = run_challenger_training(
        inputs,
        training_run_id=ident("run:inv32"),
        dataset_snapshot_id=ident("snapshot:inv32"),
        started_at=CUTOFF,
    )
    assert outcome.run.consent_reauthorized

    # An early `no` and a late report are both ineligible.
    window = f.window()
    early_no = f.report(
        "inv32-early-no",
        value=OutcomeReportValue.NO,
        reported_at=window.target_start_at + timedelta(hours=1),
        outcome_window=window,
    )
    assert early_no.timing_status is TimingStatus.EARLY
    assert not report_is_eligible(early_no, window)

    # An unknown report never resolves an outcome either.
    unknown = f.report(
        "inv32-unknown",
        value=OutcomeReportValue.UNKNOWN,
        reported_at=window.target_end_at + timedelta(hours=1),
        outcome_window=window,
    )
    assert not report_is_eligible(unknown, window)


def test_inv_33_every_metric_states_origin_dataset_hash_and_model() -> None:
    outcome = run_challenger_training(
        _two_class_inputs(),
        training_run_id=ident("run:inv33"),
        dataset_snapshot_id=ident("snapshot:inv33"),
        started_at=CUTOFF,
    )
    result = nested_out_of_fold(outcome.landmarks)
    report = build_evaluation_report(
        result,
        evaluation_report_id=ident("evaluation:inv33"),
        snapshot=outcome.snapshot,
        model_version="real-logit-challenger-0.3.0",
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        intended_use=IntendedUse.SHADOW_EVALUATION,
        protocol_version=EVALUATION_PROTOCOL_VERSION,
        created_at=CUTOFF,
        with_intervals=False,
    )
    assert report.data_origin is DataOrigin.REAL
    assert report.dataset_sha256 == outcome.snapshot.content_sha256
    assert report.model_version == "real-logit-challenger-0.3.0"
    assert report.metrics
    assert report.limitations_es


def test_inv_34_synthetic_metrics_say_simulation_only() -> None:
    outcome = run_challenger_training(
        _two_class_inputs(),
        training_run_id=ident("run:inv34"),
        dataset_snapshot_id=ident("snapshot:inv34"),
        started_at=CUTOFF,
    )
    synthetic = outcome.snapshot.model_copy(update={"data_origin": DataOrigin.SYNTHETIC})
    result = nested_out_of_fold(outcome.landmarks)
    report = build_evaluation_report(
        result,
        evaluation_report_id=ident("evaluation:inv34"),
        snapshot=synthetic,
        model_version="synthetic-reference-0.2.1",
        track_id=TrackId.SYNTHETIC_REFERENCE_V021,
        intended_use=IntendedUse.SIMULATION_ONLY,
        protocol_version=EVALUATION_PROTOCOL_VERSION,
        created_at=CUTOFF,
        with_intervals=False,
    )
    assert report.is_simulation_only
    assert any("simulation_only" in line for line in report.limitations_es)

    with pytest.raises(ValueError, match="simulation_only"):
        build_evaluation_report(
            result,
            evaluation_report_id=ident("evaluation:inv34-bad"),
            snapshot=synthetic,
            model_version="synthetic-reference-0.2.1",
            track_id=TrackId.SYNTHETIC_REFERENCE_V021,
            intended_use=IntendedUse.OPERATIONAL_SUPPORT,
            protocol_version=EVALUATION_PROTOCOL_VERSION,
            created_at=CUTOFF,
            with_intervals=False,
        )


def test_inv_35_no_adapter_turns_a_category_into_a_count_or_a_scale() -> None:
    from ml.adapters.bluba import map_value

    regulation = map_value(FieldCode.DAILY_REGULATION_STATE, "Estable con Apoyo")
    assert regulation.value == "stable_with_support"
    assert not isinstance(regulation.value, int)
    assert regulation.raw_value == "Estable con Apoyo"

    attendance = map_value(FieldCode.ATTENDANCE_STATUS, "Presente")
    assert attendance.value == "present"

    with pytest.raises(UnmappedSourceValueError):
        map_value(FieldCode.SLEEP_QUALITY, "Categoria inventada")


def test_a_single_class_evaluation_reports_counts_instead_of_a_false_auc() -> None:
    """The evaluation half of INV-19: one class produces no AUC, only counts."""

    labels = [0, 0, 0]
    probabilities = [0.1, 0.2, 0.3]
    assert auc_roc(labels, probabilities) is None
    assert average_precision(labels, probabilities) is None

    outcome = run_challenger_training(
        _single_class_inputs(),
        training_run_id=ident("run:counts"),
        dataset_snapshot_id=ident("snapshot:counts"),
        started_at=CUTOFF,
    )
    result = nested_out_of_fold(outcome.landmarks)
    report = build_evaluation_report(
        result,
        evaluation_report_id=ident("evaluation:counts"),
        snapshot=outcome.snapshot,
        model_version="real-logit-challenger-0.3.0",
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        intended_use=IntendedUse.SHADOW_EVALUATION,
        protocol_version=EVALUATION_PROTOCOL_VERSION,
        created_at=CUTOFF,
        with_intervals=False,
    )
    by_name = {metric.name: metric for metric in report.metrics}
    assert by_name["auc_roc"].status is MetricStatus.NOT_ESTIMABLE
    assert "labelled_episodes" in by_name


def test_the_authoring_review_kinds_never_share_a_capability_by_accident() -> None:
    """INV-25 support: each review kind maps to exactly one capability."""

    from rag.domain.reviews import required_capability

    evidence = required_capability(AuthoringReviewObjectType.STRATEGY, AuthoringReviewKind.EVIDENCE)
    clinical = required_capability(AuthoringReviewObjectType.STRATEGY, AuthoringReviewKind.CLINICAL)
    assert evidence is not clinical
    unmapped = required_capability(AuthoringReviewObjectType.DOCUMENT, AuthoringReviewKind.CLINICAL)
    assert unmapped is None


def test_the_run_and_the_evaluation_agree_on_the_dataset_they_read() -> None:
    """SPEC 10.5: the flywheel is only auditable if the hashes line up."""

    outcome = run_challenger_training(
        _two_class_inputs(),
        training_run_id=ident("run:agreement"),
        dataset_snapshot_id=ident("snapshot:agreement"),
        started_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    )
    assert outcome.run.dataset_sha256 == outcome.snapshot.content_sha256
