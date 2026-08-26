"""Contract invariants the models enforce, so no consumer has to remember them."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from packages.shared.domain.api import (
    FormSessionResponse,
    FormSubmitResponse,
    HumanPlanItem,
    PredictionOutputView,
    RecommendationResponse,
)
from packages.shared.domain.observation import (
    AnswerSubmission,
    DataQuality,
    FieldObservation,
    FormSession,
)
from packages.shared.domain.prediction import (
    CAPTURE_LIMIT,
    TARGET_HORIZON,
    FeatureSnapshot,
    PredictionOutput,
    TargetDefinitionVersion,
    VoiEstimate,
)
from packages.shared.domain.rag import ScenarioPredicate, ScenarioV1
from packages.shared.domain.review import (
    RecommendationInstance,
    RecommendationReview,
    StrategyExecution,
    exposure_is_eligible,
)
from packages.shared.enums import (
    AnswerInteraction,
    ApprovalStatus,
    CohortKind,
    DataOrigin,
    EntryMode,
    EstimateKind,
    ExecutionStatus,
    FieldCode,
    FormSessionKind,
    FormSessionStatus,
    IntendedUse,
    IntervalMethod,
    PredictionAbstentionReason,
    PredictionStatus,
    QuestionReason,
    RecommendationAbstentionReason,
    RecommendationResponseStatus,
    ReviewDecision,
    Role,
    RuntimeStatus,
    Source,
    SubmitStatus,
    TargetScope,
    TrackId,
    VoiStatus,
)
from tests.p1.factories import ACTOR, NOW, SUBJECT, TENANT, episode, ident, observation

# --- window ---------------------------------------------------------------


def test_the_episode_window_is_exactly_twenty_four_and_forty_eight_hours() -> None:
    built = episode()
    assert built.target_end_at - built.prediction_at == TARGET_HORIZON == timedelta(hours=24)
    assert built.capture_deadline_at - built.prediction_at == CAPTURE_LIMIT == timedelta(hours=48)
    assert built.as_of_at == built.prediction_at == built.target_start_at


def test_a_shifted_window_is_rejected() -> None:
    payload = episode().model_dump()
    payload["target_end_at"] = payload["prediction_at"] + timedelta(hours=23)
    with pytest.raises(ValidationError):
        type(episode())(**payload)


def test_the_target_window_is_open_at_the_start_and_closed_at_the_end() -> None:
    built = episode()
    assert not built.contains(built.target_start_at)
    assert built.contains(built.target_end_at)
    assert built.contains(built.target_start_at + timedelta(seconds=1))


# --- observations ---------------------------------------------------------


def test_a_field_cannot_be_reported_from_a_source_that_is_not_allowed() -> None:
    with pytest.raises(ValidationError):
        observation("bad", field_code=FieldCode.SLEEP_HOURS, value=8.0, source=Source.SCHOOL)


def test_explicit_unknown_records_no_value() -> None:
    with pytest.raises(ValidationError):
        observation("unknown-with-value", entry_mode=EntryMode.EXPLICIT_UNKNOWN, value=False)
    row = observation("unknown", entry_mode=EntryMode.EXPLICIT_UNKNOWN, value=None)
    assert row.value is None
    assert not row.trains_defaults
    assert not row.feeds_primary_real_model


def test_accepted_defaults_never_train_the_estimator_or_the_real_model() -> None:
    accepted = observation("accepted", entry_mode=EntryMode.DEFAULT_ACCEPTED)
    assert not accepted.trains_defaults
    assert not accepted.feeds_primary_real_model


def test_an_edited_default_describes_the_day_but_never_trains_the_estimator() -> None:
    edited = observation("edited", entry_mode=EntryMode.DEFAULT_EDITED, value=True)
    assert not edited.trains_defaults
    assert edited.feeds_primary_real_model


def test_an_import_needs_its_approved_mapping() -> None:
    with pytest.raises(ValidationError):
        observation("import", entry_mode=EntryMode.IMPORTED_OBSERVED)
    row = observation(
        "import-ok",
        entry_mode=EntryMode.IMPORTED_OBSERVED,
        source_mapping_id=ident("mapping"),
    )
    assert row.trains_defaults


def test_only_an_import_carries_a_source_mapping() -> None:
    with pytest.raises(ValidationError):
        observation("manual-with-mapping", source_mapping_id=ident("mapping"))


def test_local_date_must_be_derived_from_effective_at() -> None:
    payload = observation("row").model_dump()
    payload["local_date"] = payload["local_date"] + timedelta(days=1)
    with pytest.raises(ValidationError):
        FieldObservation(**payload)


def test_an_unknown_answer_carries_no_value_and_a_default_answer_carries_its_presentation() -> None:
    assert (
        AnswerSubmission(
            field_code=FieldCode.FOOD_CHANGES, interaction=AnswerInteraction.UNKNOWN
        ).value
        is None
    )
    with pytest.raises(ValidationError):
        AnswerSubmission(
            field_code=FieldCode.FOOD_CHANGES,
            interaction=AnswerInteraction.ACCEPT_DEFAULT,
            value=False,
        )


def test_dqi_is_the_product_of_its_three_components() -> None:
    quality = DataQuality(
        coverage=0.8,
        recency=0.5,
        consistency=0.9,
        dqi=0.8 * 0.5 * 0.9,
        window_days=14,
        required_fields=(FieldCode.SLEEP_QUALITY,),
    )
    assert quality.dqi == pytest.approx(0.36)
    with pytest.raises(ValidationError):
        DataQuality(
            coverage=0.8,
            recency=0.5,
            consistency=0.9,
            dqi=0.5,
            window_days=14,
            required_fields=(FieldCode.SLEEP_QUALITY,),
        )


def _session(**overrides: object) -> FormSession:
    payload: dict[str, object] = {
        "form_session_id": ident("session"),
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "actor_id": ACTOR,
        "source": Source.HOME,
        "session_kind": FormSessionKind.CAREGIVER_DAILY,
        "status": FormSessionStatus.DRAFT,
        "audit_mode": False,
        "form_policy_version": "form-0.3.0",
        "opened_at": NOW,
    }
    payload.update(overrides)
    return FormSession(**payload)


def test_a_submitted_session_records_when_it_closed() -> None:
    with pytest.raises(ValidationError):
        _session(status=FormSessionStatus.SUBMITTED)
    session = _session(status=FormSessionStatus.SUBMITTED, submitted_at=NOW + timedelta(minutes=5))
    assert session.submitted_at is not None


def test_a_session_either_creates_an_episode_or_links_to_one() -> None:
    with pytest.raises(ValidationError):
        _session(
            status=FormSessionStatus.SUBMITTED,
            submitted_at=NOW,
            prediction_episode_id=ident("a"),
            linked_prediction_episode_id=ident("b"),
        )


def test_a_professional_observation_session_is_never_audited() -> None:
    with pytest.raises(ValidationError):
        _session(session_kind=FormSessionKind.PROFESSIONAL_OBSERVATION, audit_mode=True)


# --- target definition ----------------------------------------------------


def _target(**overrides: object) -> TargetDefinitionVersion:
    payload: dict[str, object] = {
        "target_definition_version": "target-demo-1",
        "scope": TargetScope.DEMO_FIXTURE,
        "tenant_id": None,
        "question_es": "¿Ocurrió un episodio mayor de desregulación?",
        "severity_anchors_es": ("Leve", "Moderada", "Severa"),
        "eligible_reporter_roles": frozenset({Role.CAREGIVER}),
        "effective_from": NOW,
        "evidence_basis": "Fixture de demostración, sin valor clínico.",
        "approval_status": ApprovalStatus.DRAFT,
        "content_sha256": "0" * 64,
    }
    payload.update(overrides)
    return TargetDefinitionVersion(**payload)


def test_a_tenant_target_needs_a_tenant_and_a_demo_target_does_not_have_one() -> None:
    with pytest.raises(ValidationError):
        _target(scope=TargetScope.TENANT, tenant_id=None)
    with pytest.raises(ValidationError):
        _target(scope=TargetScope.DEMO_FIXTURE, tenant_id=TENANT)


def test_activating_a_target_requires_a_clinical_review() -> None:
    with pytest.raises(ValidationError):
        _target(approval_status=ApprovalStatus.ACTIVE)
    assert _target(approval_status=ApprovalStatus.ACTIVE, clinical_review_id=ident("review"))


def test_a_demo_fixture_target_forces_synthetic_outcomes() -> None:
    assert _target().forces_synthetic_outcomes is True
    assert _target(scope=TargetScope.TENANT, tenant_id=TENANT).forces_synthetic_outcomes is False


# --- snapshots and outputs ------------------------------------------------


def test_a_synthetic_row_invalidates_a_real_snapshot() -> None:
    with pytest.raises(ValidationError):
        FeatureSnapshot(
            feature_snapshot_id=ident("snapshot"),
            tenant_id=TENANT,
            subject_id=SUBJECT,
            prediction_episode_id=ident("episode"),
            as_of_at=NOW,
            input_data_origin=DataOrigin.REAL,
            schema_version="snapshot-1",
            observed_data_origins=frozenset({DataOrigin.REAL, DataOrigin.SYNTHETIC}),
            content_sha256="0" * 64,
        )


def _output(**overrides: object) -> PredictionOutput:
    payload: dict[str, object] = {
        "prediction_output_id": ident("output"),
        "tenant_id": TENANT,
        "prediction_episode_id": ident("episode"),
        "track_id": TrackId.REAL_PERSONAL_BASELINE_V1,
        "intended_use": IntendedUse.OPERATIONAL_SUPPORT,
        "status": PredictionStatus.ABSTAINED,
        "estimate_kind": EstimateKind.PERSONAL_OBSERVED_EPISODE_RATE,
        "abstention_reasons": (PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES,),
        "model_version": "baseline-0.3.0",
        "input_data_origin": DataOrigin.REAL,
        "created_at": NOW,
    }
    payload.update(overrides)
    return PredictionOutput(**payload)


def test_an_abstention_states_a_reason_and_carries_no_number() -> None:
    assert _output().probability is None
    with pytest.raises(ValidationError):
        _output(abstention_reasons=())
    with pytest.raises(ValidationError):
        _output(probability=0.2)


def test_a_visible_baseline_needs_probability_interval_and_method() -> None:
    with pytest.raises(ValidationError):
        _output(status=PredictionStatus.OK, abstention_reasons=(), probability=0.2)
    output = _output(
        status=PredictionStatus.OK,
        abstention_reasons=(),
        probability=0.2,
        interval={"lower": 0.05, "upper": 0.45},
        interval_method=IntervalMethod.BETA_POSTERIOR_QUANTILE,
    )
    assert output.interval is not None


def test_the_simulation_track_never_runs_on_real_input_and_is_never_a_probability() -> None:
    with pytest.raises(ValidationError):
        _output(
            track_id=TrackId.SYNTHETIC_REFERENCE_V021,
            intended_use=IntendedUse.SIMULATION_ONLY,
            estimate_kind=EstimateKind.SIMULATION_SCORE,
            input_data_origin=DataOrigin.REAL,
        )
    output = _output(
        track_id=TrackId.SYNTHETIC_REFERENCE_V021,
        intended_use=IntendedUse.SIMULATION_ONLY,
        estimate_kind=EstimateKind.SIMULATION_SCORE,
        input_data_origin=DataOrigin.SYNTHETIC,
        status=PredictionStatus.OK,
        abstention_reasons=(),
        simulation_score=0.42,
    )
    assert output.probability is None and output.interval is None


def test_the_challenger_stores_a_shadow_score_and_is_never_exposed() -> None:
    output = _output(
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        intended_use=IntendedUse.SHADOW_EVALUATION,
        estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE,
        status=PredictionStatus.OK,
        abstention_reasons=(),
        shadow_score=0.3,
    )
    assert output.is_exposable_to_caregiver is False
    with pytest.raises(ValidationError):
        PredictionOutputView(
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
            intended_use=IntendedUse.SHADOW_EVALUATION,
            status=PredictionStatus.OK,
            estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE,
            model_version="challenger-0.3.0",
            input_data_origin=DataOrigin.REAL,
        )


def test_a_track_cannot_borrow_another_tracks_meaning() -> None:
    with pytest.raises(ValidationError):
        _output(estimate_kind=EstimateKind.SIMULATION_SCORE)
    with pytest.raises(ValidationError):
        _output(intended_use=IntendedUse.SIMULATION_ONLY)


def test_the_output_contract_has_no_confidence_field() -> None:
    assert "confidence" not in PredictionOutput.model_fields
    assert "confidence" not in PredictionOutputView.model_fields


# --- VoI ------------------------------------------------------------------


def test_unavailable_voi_is_null_never_zero() -> None:
    estimate = VoiEstimate(field_code=FieldCode.SLEEP_QUALITY, status=VoiStatus.UNAVAILABLE_MODEL)
    assert estimate.voi_nats is None
    with pytest.raises(ValidationError):
        VoiEstimate(
            field_code=FieldCode.SLEEP_QUALITY,
            status=VoiStatus.UNAVAILABLE_MODEL,
            voi_nats=0.0,
        )


def test_an_available_voi_records_the_versions_it_used() -> None:
    with pytest.raises(ValidationError):
        VoiEstimate(field_code=FieldCode.SLEEP_QUALITY, status=VoiStatus.AVAILABLE, voi_nats=0.1)
    assert VoiEstimate(
        field_code=FieldCode.SLEEP_QUALITY,
        status=VoiStatus.AVAILABLE,
        voi_nats=0.1,
        q_estimator_version="defaults-0.3.0",
        conditional_model_version="challenger-0.3.0",
        cutoff_at=NOW,
    )


# --- scenario and predicate ----------------------------------------------


def test_a_scenario_only_carries_allowlisted_fields() -> None:
    with pytest.raises(ValidationError):
        ScenarioV1(field_values={FieldCode.NOTES: "algo"})
    with pytest.raises(ValidationError):
        ScenarioV1(field_values={FieldCode.SLEEP_QUALITY: "reparador"})


def test_scenario_tags_are_deduplicated_and_sorted_before_hashing() -> None:
    scenario = ScenarioV1(
        field_values={FieldCode.SLEEP_QUALITY: "interrupted"},
        context_tags=("therapy", "therapy", "home"),
        profile_tags=("sensory:auditory_hypersensitive",),
    )
    assert scenario.context_tags == ("home", "therapy")
    payload = scenario.canonical_payload()
    assert payload["context_tags"] == ["home", "therapy"]


def test_matching_is_fail_closed() -> None:
    scenario = ScenarioV1(
        field_values={FieldCode.SLEEP_QUALITY: "interrupted", FieldCode.ALERTNESS: "high"},
        context_tags=("therapy",),
        profile_tags=("sensory:auditory_hypersensitive",),
        contraindication_tags=("weighted_vest",),
    )
    assert ScenarioPredicate(
        required_field_values={FieldCode.SLEEP_QUALITY: ("interrupted",)}
    ).matches(scenario)
    assert not ScenarioPredicate(required_field_values={FieldCode.GI_STATUS: ("normal",)}).matches(
        scenario
    )
    assert not ScenarioPredicate(excluded_field_values={FieldCode.ALERTNESS: ("high",)}).matches(
        scenario
    )
    assert not ScenarioPredicate(contraindication_tags=("weighted_vest",)).matches(scenario)
    assert not ScenarioPredicate(required_profile_tags=("sensory:tactile_avoidant",)).matches(
        scenario
    )


def test_set_implication_is_sound_and_fails_closed() -> None:
    strategy = ScenarioPredicate(
        required_field_values={FieldCode.SLEEP_QUALITY: ("interrupted", "restorative")},
        contraindication_tags=("weighted_vest",),
    )
    narrower = ScenarioPredicate(
        required_field_values={FieldCode.SLEEP_QUALITY: ("interrupted",)},
        contraindication_tags=("weighted_vest",),
    )
    assert narrower.implies(strategy)
    assert not strategy.implies(narrower)
    assert not ScenarioPredicate().implies(strategy)


# --- review, plans and executions ----------------------------------------


def _instance(**overrides: object) -> RecommendationInstance:
    payload: dict[str, object] = {
        "recommendation_instance_id": ident("instance"),
        "tenant_id": TENANT,
        "subject_id": SUBJECT,
        "prediction_episode_id": ident("episode"),
        "scenario_hash": "a" * 64,
        "runtime_status": RuntimeStatus.ABSTAINED,
        "abstention_reasons": (RecommendationAbstentionReason.CORPUS_NOT_READY,),
        "created_at": NOW,
    }
    payload.update(overrides)
    return RecommendationInstance(**payload)


def test_an_abstained_instance_keeps_its_reason_and_no_strategies() -> None:
    assert _instance().strategy_version_ids == ()
    with pytest.raises(ValidationError):
        _instance(strategy_version_ids=(ident("strategy"),))


def test_an_instance_never_stores_a_review_status() -> None:
    assert "review_status" not in RecommendationInstance.model_fields


def test_a_matched_instance_never_exceeds_three_strategies() -> None:
    with pytest.raises(ValidationError):
        _instance(
            runtime_status=RuntimeStatus.MATCHED,
            abstention_reasons=(),
            catalog_version="catalog-0.3.0",
            corpus_version="corpus-1",
            strategy_version_ids=tuple(ident(f"s{index}") for index in range(4)),
        )


def _review(decision: ReviewDecision, **overrides: object) -> RecommendationReview:
    payload: dict[str, object] = {
        "review_id": ident("review"),
        "tenant_id": TENANT,
        "recommendation_instance_id": ident("instance"),
        "strategy_version_id": ident("strategy"),
        "decision": decision,
        "reviewed_by": ACTOR,
        "reviewer_role": Role.PROFESSIONAL,
        "reviewed_at": NOW,
        "ingested_at": NOW,
    }
    payload.update(overrides)
    return RecommendationReview(**payload)


def test_a_substitution_references_the_plan_it_created() -> None:
    with pytest.raises(ValidationError):
        _review(ReviewDecision.HUMAN_PLAN_SUBSTITUTED)
    with pytest.raises(ValidationError):
        _review(ReviewDecision.APPROVED, human_plan_version_id=ident("plan"))
    assert _review(
        ReviewDecision.HUMAN_PLAN_SUBSTITUTED, human_plan_version_id=ident("plan")
    ).is_favourable


def test_deferred_is_not_an_acceptance() -> None:
    assert _review(ReviewDecision.DEFERRED).is_favourable is False


def _execution(**overrides: object) -> StrategyExecution:
    payload: dict[str, object] = {
        "strategy_execution_id": ident("execution"),
        "tenant_id": TENANT,
        "recommendation_instance_id": ident("instance"),
        "strategy_version_id": ident("strategy"),
        "status": ExecutionStatus.APPLIED,
        "actor_id": ACTOR,
        "actor_role": Role.CAREGIVER,
        "recorded_at": NOW + timedelta(hours=2),
        "applied_at": NOW + timedelta(hours=1),
        "ingested_at": NOW + timedelta(hours=2),
    }
    payload.update(overrides)
    return StrategyExecution(**payload)


def test_an_execution_references_a_strategy_or_a_plan_but_never_both() -> None:
    with pytest.raises(ValidationError):
        _execution(human_plan_version_id=ident("plan"))
    with pytest.raises(ValidationError):
        _execution(strategy_version_id=None)


def test_applied_at_may_be_retrospective_but_never_in_the_future() -> None:
    with pytest.raises(ValidationError):
        _execution(applied_at=NOW + timedelta(hours=3))
    with pytest.raises(ValidationError):
        _execution(status=ExecutionStatus.NOT_APPLIED)


def test_exposure_eligibility_follows_the_chronology() -> None:
    review = _review(ReviewDecision.APPROVED, reviewed_at=NOW + timedelta(minutes=30))
    execution = _execution()
    assert exposure_is_eligible(
        instance_created_at=NOW,
        review=review,
        execution=execution,
        target_end_at=NOW + timedelta(hours=24),
        outcome_occurred_at=NOW + timedelta(hours=5),
    )
    # Applied after the event it is meant to precede.
    assert not exposure_is_eligible(
        instance_created_at=NOW,
        review=review,
        execution=execution,
        target_end_at=NOW + timedelta(hours=24),
        outcome_occurred_at=NOW + timedelta(minutes=30),
    )
    # Applied after the window closed.
    assert not exposure_is_eligible(
        instance_created_at=NOW,
        review=review,
        execution=_execution(
            applied_at=NOW + timedelta(hours=30), recorded_at=NOW + timedelta(hours=31)
        ),
        target_end_at=NOW + timedelta(hours=24),
        outcome_occurred_at=None,
    )


def test_a_human_plan_item_never_shows_rag_citations() -> None:
    with pytest.raises(ValidationError):
        HumanPlanItem(
            human_plan_version_id=ident("plan"),
            action_text_es="Texto del profesional.",
            citations=(
                {
                    "citation_id": ident("citation"),
                    "claim_id": ident("claim"),
                    "locator": "p. 1",
                    "quoted_text": "algo",
                    "canonical_url": "https://example.org/doc",
                },
            ),
        )


# --- API envelopes --------------------------------------------------------


def test_submit_status_matches_the_references_it_returns() -> None:
    with pytest.raises(ValidationError):
        FormSubmitResponse(
            form_session_id=ident("session"),
            status=SubmitStatus.EPISODE_CREATED,
            submitted_at=NOW,
        )
    with pytest.raises(ValidationError):
        FormSubmitResponse(
            form_session_id=ident("session"),
            status=SubmitStatus.TARGET_DEFINITION_UNAVAILABLE,
            submitted_at=NOW,
            prediction_episode_id=ident("episode"),
        )
    assert (
        FormSubmitResponse(
            form_session_id=ident("session"),
            status=SubmitStatus.TARGET_DEFINITION_UNAVAILABLE,
            submitted_at=NOW,
        ).prediction_episode_id
        is None
    )


def _question(field_code: FieldCode, with_default: bool = False) -> dict[str, object]:
    question: dict[str, object] = {"field_code": field_code, "reason": QuestionReason.STALENESS}
    if with_default:
        question["default"] = {
            "presentation_id": ident("presentation"),
            "value": False,
            "candidate_count": 36,
            "posterior_mean": 0.8409,
            "lower_bound": 0.7431,
            "n_observations": 42,
            "estimator_version": "defaults-0.3.0",
        }
    return question


def test_an_audited_session_returns_no_defaults() -> None:
    with pytest.raises(ValidationError):
        FormSessionResponse(
            form_session_id=ident("session"),
            subject_id=SUBJECT,
            source=Source.HOME,
            session_kind=FormSessionKind.CAREGIVER_DAILY,
            opened_at=NOW,
            audit_mode=True,
            form_policy_version="form-0.3.0",
            voi_status=VoiStatus.UNAVAILABLE_MODEL,
            highlighted=(_question(FieldCode.FOOD_CHANGES, with_default=True),),
        )


def test_a_field_appears_once_across_highlighted_and_tail() -> None:
    with pytest.raises(ValidationError):
        FormSessionResponse(
            form_session_id=ident("session"),
            subject_id=SUBJECT,
            source=Source.HOME,
            session_kind=FormSessionKind.CAREGIVER_DAILY,
            opened_at=NOW,
            audit_mode=False,
            form_policy_version="form-0.3.0",
            voi_status=VoiStatus.UNAVAILABLE_MODEL,
            highlighted=(_question(FieldCode.SLEEP_QUALITY),),
            tail=(_question(FieldCode.SLEEP_QUALITY),),
        )


def test_nothing_is_exposed_while_every_recommendation_is_pending() -> None:
    response = RecommendationResponse(
        status=RecommendationResponseStatus.AWAITING_PROFESSIONAL_REVIEW,
        recommendation_instance_id=ident("instance"),
    )
    assert response.items == ()


def test_an_abstained_recommendation_states_its_reason() -> None:
    with pytest.raises(ValidationError):
        RecommendationResponse(
            status=RecommendationResponseStatus.ABSTAINED,
            recommendation_instance_id=ident("instance"),
        )


def test_the_episode_response_never_carries_a_band_or_a_decision_policy() -> None:
    from packages.shared.domain.api import PredictionEpisodeResponse

    fields = PredictionEpisodeResponse.model_fields
    assert fields["risk_band"].annotation is type(None)
    assert fields["decision_policy_version"].annotation is type(None)


def test_a_cohort_demo_episode_never_carries_real_input_data() -> None:
    with pytest.raises(ValidationError):
        episode_payload = episode().model_dump()
        episode_payload["cohort_kind"] = CohortKind.DEMO_FIXTURE
        episode_payload["input_data_origin"] = DataOrigin.REAL
        type(episode())(**episode_payload)
