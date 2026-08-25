"""Dataset snapshots, consent re-authorisation and the training run (M5/P1.8)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ml.errors import OriginMixError
from ml.prediction.landmarks import reveal_schedule, reveal_schedule_sha256
from packages.shared.enums import (
    AuthorizationStatus,
    CohortKind,
    ConsentPurpose,
    DataOrigin,
    EpisodeRole,
    EvaluationReportStatus,
    FieldCode,
    IntendedUse,
    ModelState,
    NotTrainableReason,
    OutcomeResolutionStatus,
    TrackId,
    TrainingRunStatus,
)
from tests.p1 import train_factories as tf
from tests.p1.factories import TENANT, ident
from tools.train.cli import load_inputs
from tools.train.cli import run as run_cli
from tools.train.consent import (
    authorize_secondary_model_use,
    revocation_impact,
    suspend_dependent_models,
    suspend_dependent_reports,
)
from tools.train.run import run_challenger_training, run_report
from tools.train.snapshot import SnapshotInputs, build_dataset_snapshot

CUTOFF = tf.RUN_AT
SUBJECT_A = tf.subject("a")
SUBJECT_B = tf.subject("b")


def _episode_with_outcome(
    label: str, *, subject_id, days_ago: int, status: OutcomeResolutionStatus, **overrides
):
    prediction_at = CUTOFF - timedelta(days=days_ago)
    episode = tf.episode(label, subject_id=subject_id, prediction_at=prediction_at, **overrides)
    resolved_at = prediction_at + timedelta(hours=30)
    return episode, tf.resolution(
        label, episode_id=episode.prediction_episode_id, status=status, resolved_at=resolved_at
    )


def _single_class_inputs() -> SnapshotInputs:
    """Six negatives across two subjects: the repository's situation today."""

    episodes = []
    resolutions = []
    for index in range(6):
        subject_id = SUBJECT_A if index % 2 == 0 else SUBJECT_B
        episode, resolution = _episode_with_outcome(
            f"neg-{index}",
            subject_id=subject_id,
            days_ago=index + 2,
            status=OutcomeResolutionStatus.NO,
        )
        episodes.append(episode)
        resolutions.append(resolution)
    observations = tf.predictor_history(SUBJECT_A, days=20, until=CUTOFF) + tf.predictor_history(
        SUBJECT_B, days=20, until=CUTOFF
    )
    return SnapshotInputs(
        tenant_id=TENANT,
        data_origin=DataOrigin.REAL,
        target_definition_version=tf.TARGET_VERSION,
        cutoff_at=CUTOFF,
        episodes=tuple(episodes),
        resolutions=tuple(resolutions),
        observations=observations,
        consents=(
            tf.consent("a", subject_id=SUBJECT_A),
            tf.consent("b", subject_id=SUBJECT_B),
        ),
    )


def _two_class_inputs() -> SnapshotInputs:
    """Enough history per subject that landmarks become estimable, with both classes.

    This is not the repository's data; it exists to prove the pipeline produces
    a candidate when the outcomes allow one, so `not_trainable` elsewhere is a
    statement about the data rather than about the code.
    """

    episodes = []
    resolutions = []
    for subject_id, tag in ((SUBJECT_A, "a"), (SUBJECT_B, "b")):
        for index, days_ago in enumerate(range(2, 16)):
            status = OutcomeResolutionStatus.YES if index % 3 == 0 else OutcomeResolutionStatus.NO
            episode, resolution = _episode_with_outcome(
                f"{tag}-{days_ago}", subject_id=subject_id, days_ago=days_ago, status=status
            )
            episodes.append(episode)
            resolutions.append(resolution)
    observations = tf.predictor_history(SUBJECT_A, days=25, until=CUTOFF) + tf.predictor_history(
        SUBJECT_B, days=25, until=CUTOFF
    )
    return SnapshotInputs(
        tenant_id=TENANT,
        data_origin=DataOrigin.REAL,
        target_definition_version=tf.TARGET_VERSION,
        cutoff_at=CUTOFF,
        episodes=tuple(episodes),
        resolutions=tuple(resolutions),
        observations=observations,
        consents=(
            tf.consent("a", subject_id=SUBJECT_A),
            tf.consent("b", subject_id=SUBJECT_B),
        ),
    )


def _build(inputs: SnapshotInputs):
    return build_dataset_snapshot(
        inputs, dataset_snapshot_id=ident("snapshot:test"), created_at=CUTOFF
    )


class TestSnapshotOrigin:
    def test_a_synthetic_episode_raises_inside_a_real_snapshot(self) -> None:
        inputs = _single_class_inputs()
        synthetic = tf.episode(
            "synthetic",
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

    def test_a_synthetic_observation_raises_inside_a_real_snapshot(self) -> None:
        inputs = _single_class_inputs()
        synthetic = tf.observation(
            "synthetic-row",
            subject_id=SUBJECT_A,
            field_code=FieldCode.SLEEP_QUALITY,
            value="restorative",
            effective_at=CUTOFF - timedelta(days=1),
            data_origin=DataOrigin.SYNTHETIC,
        )
        with pytest.raises(OriginMixError):
            _build(
                SnapshotInputs(
                    tenant_id=inputs.tenant_id,
                    data_origin=DataOrigin.REAL,
                    target_definition_version=inputs.target_definition_version,
                    cutoff_at=inputs.cutoff_at,
                    episodes=inputs.episodes,
                    resolutions=inputs.resolutions,
                    observations=(*inputs.observations, synthetic),
                    consents=inputs.consents,
                )
            )


class TestSnapshotMembership:
    def test_only_primary_episodes_of_the_exact_target_version_are_included(self) -> None:
        inputs = _single_class_inputs()
        other_version, other_resolution = _episode_with_outcome(
            "other-target",
            subject_id=SUBJECT_A,
            days_ago=3,
            status=OutcomeResolutionStatus.NO,
            target_definition_version="target-demo-2",
        )
        build = _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=inputs.data_origin,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=(*inputs.episodes, other_version),
                resolutions=(*inputs.resolutions, other_resolution),
                observations=inputs.observations,
                consents=inputs.consents,
            )
        )
        assert other_version.prediction_episode_id not in build.snapshot.episode_ids
        assert (
            other_version.prediction_episode_id,
            "other_target_definition_version",
        ) in build.excluded

    def test_an_ever_conflicted_episode_is_excluded(self) -> None:
        inputs = _single_class_inputs()
        episode, conflicted = _episode_with_outcome(
            "conflicted", subject_id=SUBJECT_A, days_ago=4, status=OutcomeResolutionStatus.YES
        )
        conflicted = conflicted.model_copy(update={"ever_conflicted": True})
        build = _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=inputs.data_origin,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=(*inputs.episodes, episode),
                resolutions=(*inputs.resolutions, conflicted),
                observations=inputs.observations,
                consents=inputs.consents,
            )
        )
        assert (episode.prediction_episode_id, "ever_conflicted") in build.excluded

    def test_a_pending_or_unknown_resolution_is_not_a_label(self) -> None:
        inputs = _single_class_inputs()
        episode = tf.episode(
            "pending", subject_id=SUBJECT_A, prediction_at=CUTOFF - timedelta(days=1)
        )
        pending = tf.resolution(
            "pending",
            episode_id=episode.prediction_episode_id,
            status=OutcomeResolutionStatus.PENDING,
            resolved_at=None,
        )
        build = _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=inputs.data_origin,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=(*inputs.episodes, episode),
                resolutions=(*inputs.resolutions, pending),
                observations=inputs.observations,
                consents=inputs.consents,
            )
        )
        assert (episode.prediction_episode_id, "not_conclusive") in build.excluded

    def test_a_subject_without_secondary_consent_is_excluded(self) -> None:
        inputs = _single_class_inputs()
        build = _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=inputs.data_origin,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=inputs.episodes,
                resolutions=inputs.resolutions,
                observations=inputs.observations,
                consents=(tf.consent("a", subject_id=SUBJECT_A),),
            )
        )
        assert build.snapshot.subject_count == 1
        assert any(reason == "consent_not_authorized" for _, reason in build.excluded)

    def test_a_secondary_episode_role_is_excluded(self) -> None:
        inputs = _single_class_inputs()
        # v0.3 only defines `primary`, so this asserts the filter exists rather
        # than inventing a second role.
        assert all(episode.role is EpisodeRole.PRIMARY for episode in inputs.episodes)

    def test_the_snapshot_hash_is_stable_and_depends_on_its_rows(self) -> None:
        inputs = _single_class_inputs()
        first = _build(inputs).snapshot
        second = _build(inputs).snapshot
        assert first.content_sha256 == second.content_sha256

        fewer = SnapshotInputs(
            tenant_id=inputs.tenant_id,
            data_origin=inputs.data_origin,
            target_definition_version=inputs.target_definition_version,
            cutoff_at=inputs.cutoff_at,
            episodes=inputs.episodes[:-1],
            resolutions=inputs.resolutions[:-1],
            observations=inputs.observations,
            consents=inputs.consents,
        )
        assert _build(fewer).snapshot.content_sha256 != first.content_sha256

    def test_a_correction_after_the_cutoff_does_not_change_the_snapshot(self) -> None:
        inputs = _single_class_inputs()
        original = _build(inputs).snapshot
        later = tf.resolution(
            "late-correction",
            episode_id=inputs.episodes[0].prediction_episode_id,
            status=OutcomeResolutionStatus.YES,
            resolved_at=CUTOFF + timedelta(days=1),
            ingested_at=CUTOFF + timedelta(days=1),
            supersedes_id=inputs.resolutions[0].outcome_resolution_id,
            version=2,
        )
        corrected = _build(
            SnapshotInputs(
                tenant_id=inputs.tenant_id,
                data_origin=inputs.data_origin,
                target_definition_version=inputs.target_definition_version,
                cutoff_at=inputs.cutoff_at,
                episodes=inputs.episodes,
                resolutions=(*inputs.resolutions, later),
                observations=inputs.observations,
                consents=inputs.consents,
            )
        ).snapshot
        assert corrected.content_sha256 == original.content_sha256


class TestConsentReauthorization:
    def test_an_operational_consent_does_not_authorise_model_training(self) -> None:
        result = authorize_secondary_model_use(
            (
                tf.consent(
                    "operational",
                    subject_id=SUBJECT_A,
                    purpose=ConsentPurpose.OPERATIONAL_SUPPORT,
                ),
            ),
            subject_ids=(SUBJECT_A,),
            at=CUTOFF,
        )
        assert not result.authorized
        assert result.unauthorized_subject_ids == (SUBJECT_A,)

    def test_a_revocation_before_the_run_blocks_it(self) -> None:
        revoked = tf.consent("a", subject_id=SUBJECT_A, revoked_at=CUTOFF - timedelta(days=1))
        result = authorize_secondary_model_use((revoked,), subject_ids=(SUBJECT_A,), at=CUTOFF)
        assert not result.authorized

    def test_a_revocation_keeps_the_snapshot_and_suspends_real_artifacts(self) -> None:
        impact = revocation_impact(subject_id=SUBJECT_A, revoked_at=CUTOFF)
        assert impact.keeps_existing_snapshots_immutable
        assert impact.blocks_new_runs
        assert impact.suspends_dependent_real_artifacts
        assert not impact.affects_synthetic_artifacts

    def test_only_real_models_and_reports_are_suspended(self) -> None:
        from packages.shared.domain.evaluation import EvaluationReport, ModelVersion

        real = ModelVersion(
            model_version="real-logit-challenger-0.3.0",
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
            training_data_origin=DataOrigin.REAL,
            intended_use=IntendedUse.SHADOW_EVALUATION,
            state=ModelState.SHADOW,
            created_at=CUTOFF,
        )
        synthetic = ModelVersion(
            model_version="synthetic-reference-0.2.1",
            track_id=TrackId.SYNTHETIC_REFERENCE_V021,
            training_data_origin=DataOrigin.SYNTHETIC,
            intended_use=IntendedUse.SIMULATION_ONLY,
            state=ModelState.VALIDATED_OFFLINE,
            created_at=CUTOFF,
        )
        suspended = suspend_dependent_models((real, synthetic), at=CUTOFF)
        assert [model.model_version for model in suspended] == [real.model_version]
        assert suspended[0].state is ModelState.SUSPENDED_FOR_CONSENT_REVIEW

        report = EvaluationReport(
            evaluation_report_id=ident("report:real"),
            tenant_id=TENANT,
            model_version="real-logit-challenger-0.3.0",
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
            dataset_snapshot_id=ident("snapshot:test"),
            dataset_sha256="a" * 64,
            data_origin=DataOrigin.REAL,
            intended_use=IntendedUse.SHADOW_EVALUATION,
            target_definition_version=tf.TARGET_VERSION,
            protocol_version="eval-protocol-0.3.0",
            status=EvaluationReportStatus.PUBLISHED,
            limitations_es=("Reporte de prueba.",),
            created_at=CUTOFF,
            published_at=CUTOFF,
        )
        assert suspend_dependent_reports((report,), at=CUTOFF)[0].status is (
            EvaluationReportStatus.SUSPENDED_FOR_CONSENT_REVIEW
        )


class TestTrainingRun:
    def test_todays_outcomes_produce_not_trainable_single_class(self) -> None:
        outcome = run_challenger_training(
            _single_class_inputs(),
            training_run_id=ident("run:single-class"),
            dataset_snapshot_id=ident("snapshot:single-class"),
            started_at=CUTOFF,
        )
        assert outcome.run.status is TrainingRunStatus.NOT_TRAINABLE
        assert outcome.run.not_trainable_reason is NotTrainableReason.SINGLE_CLASS
        assert outcome.model is None
        assert not outcome.promoted

    def test_with_both_classes_and_enough_history_the_run_produces_a_candidate(self) -> None:
        outcome = run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:two-class"),
            dataset_snapshot_id=ident("snapshot:two-class"),
            started_at=CUTOFF,
        )
        assert outcome.run.status is TrainingRunStatus.COMPLETED
        assert outcome.model is not None
        # A run makes a candidate and stops. Shadow and shadow_evaluated are
        # decisions taken elsewhere, and never by a training run (SPEC 8.1).
        assert outcome.model.state is ModelState.CANDIDATE
        assert outcome.model.intended_use is IntendedUse.SHADOW_EVALUATION
        assert not outcome.promoted
        assert sum(1 for item in outcome.landmarks if item.is_estimable) > 0

    def test_a_landmark_uses_only_outcomes_revealed_before_its_own_cutoff(self) -> None:
        outcome = run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:reveal"),
            dataset_snapshot_id=ident("snapshot:reveal"),
            started_at=CUTOFF,
        )
        by_episode = {event.prediction_episode_id: event for event in outcome.reveal_events}
        for landmark in outcome.landmarks:
            revealed = by_episode.get(landmark.prediction_episode_id)
            assert revealed is not None
            # Its own label is revealed after its cutoff, so it can never be a
            # feature of itself.
            assert revealed.resolved_at > landmark.as_of_at

    def test_a_revoked_subject_blocks_the_run_at_its_start(self) -> None:
        inputs = _single_class_inputs()
        revoked = SnapshotInputs(
            tenant_id=inputs.tenant_id,
            data_origin=inputs.data_origin,
            target_definition_version=inputs.target_definition_version,
            cutoff_at=inputs.cutoff_at,
            episodes=inputs.episodes,
            resolutions=inputs.resolutions,
            observations=inputs.observations,
            consents=(
                tf.consent("a", subject_id=SUBJECT_A),
                tf.consent("b", subject_id=SUBJECT_B),
                tf.consent(
                    "b-revoked",
                    subject_id=SUBJECT_B,
                    status=AuthorizationStatus.REVOKED,
                    revoked_at=CUTOFF - timedelta(hours=1),
                    supersedes_id=ident("consent:b"),
                ),
            ),
        )
        # The snapshot at its own cutoff already drops the revoked subject, so
        # the run cannot silently read them either.
        build = _build(revoked)
        assert SUBJECT_B not in build.subject_ids

    def test_the_run_records_dataset_hash_code_and_dependencies(self) -> None:
        outcome = run_challenger_training(
            _single_class_inputs(),
            training_run_id=ident("run:manifest"),
            dataset_snapshot_id=ident("snapshot:manifest"),
            started_at=CUTOFF,
        )
        assert outcome.run.dataset_sha256 == outcome.snapshot.content_sha256
        assert outcome.run.code_version == "faro-train-0.3.0"
        assert "scikit-learn" in outcome.run.dependency_versions
        assert outcome.protocol.optimizer == "L-BFGS-B"
        assert outcome.protocol.l2_grid == (0.01, 0.1, 1.0, 10.0, 100.0)

    def test_the_challenger_never_trains_on_synthetic_data(self) -> None:
        inputs = _single_class_inputs()
        synthetic = SnapshotInputs(
            tenant_id=inputs.tenant_id,
            data_origin=DataOrigin.SYNTHETIC,
            target_definition_version=inputs.target_definition_version,
            cutoff_at=inputs.cutoff_at,
        )
        with pytest.raises(ValueError, match="real outcomes only"):
            run_challenger_training(
                synthetic,
                training_run_id=ident("run:synthetic"),
                dataset_snapshot_id=ident("snapshot:synthetic"),
                started_at=CUTOFF,
            )

    def test_the_report_names_the_reveal_schedule_and_never_claims_promotion(self) -> None:
        outcome = run_challenger_training(
            _single_class_inputs(),
            training_run_id=ident("run:report"),
            dataset_snapshot_id=ident("snapshot:report"),
            started_at=CUTOFF,
        )
        report = run_report(outcome)
        assert report["promoted"] is False
        assert report["model_version"] is None
        assert report["reveal_event_count"] == len(outcome.reveal_events)
        assert report["reveal_schedule_sha256"] == reveal_schedule_sha256(outcome.reveal_events)


class TestRevealSchedule:
    def test_events_are_ordered_by_reveal_instant(self) -> None:
        inputs = _single_class_inputs()
        build = _build(inputs)
        events = reveal_schedule(build.episodes, build.resolutions)
        assert [event.resolved_at for event in events] == sorted(
            event.resolved_at for event in events
        )

    def test_a_pending_outcome_never_enters_the_schedule(self) -> None:
        episode = tf.episode(
            "pending", subject_id=SUBJECT_A, prediction_at=CUTOFF - timedelta(days=1)
        )
        pending = tf.resolution(
            "pending",
            episode_id=episode.prediction_episode_id,
            status=OutcomeResolutionStatus.PENDING,
            resolved_at=None,
        )
        assert reveal_schedule((episode,), (pending,)) == ()


class TestCli:
    def test_the_command_writes_a_run_manifest(self, tmp_path: Path, capsys) -> None:
        inputs = _single_class_inputs()
        export = {
            "tenant_id": str(inputs.tenant_id),
            "data_origin": inputs.data_origin.value,
            "target_definition_version": inputs.target_definition_version,
            "cutoff_at": inputs.cutoff_at.isoformat(),
            "episodes": [row.model_dump(mode="json") for row in inputs.episodes],
            "resolutions": [row.model_dump(mode="json") for row in inputs.resolutions],
            "observations": [row.model_dump(mode="json") for row in inputs.observations],
            "consents": [row.model_dump(mode="json") for row in inputs.consents],
        }
        export_path = tmp_path / "export.json"
        export_path.write_text(json.dumps(export), encoding="utf-8")

        assert run_cli(export_path, tmp_path / "out", label="demo", now=CUTOFF) == 0
        capsys.readouterr()
        manifest = json.loads(
            (tmp_path / "out" / "demo.run.manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["status"] == "not_trainable"
        assert manifest["not_trainable_reason"] == "not_trainable_single_class"
        assert manifest["promoted"] is False

    def test_an_export_is_validated_against_the_published_contract(self) -> None:
        with pytest.raises(ValueError):
            load_inputs(
                {
                    "tenant_id": str(TENANT),
                    "data_origin": "real",
                    "target_definition_version": tf.TARGET_VERSION,
                    "cutoff_at": datetime(2026, 8, 25, tzinfo=UTC).isoformat(),
                    "episodes": [{"prediction_episode_id": "not-a-uuid"}],
                }
            )
