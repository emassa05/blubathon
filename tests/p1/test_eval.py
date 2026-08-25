"""Metrics, the versioned protocol, clustered bootstrap and reports (M5/P1.9)."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sklearn.metrics import average_precision_score

from ml.eval.bootstrap import cluster_bootstrap
from ml.eval.metrics import (
    auc_roc,
    average_precision,
    brier_score,
    calibration_fit,
    has_both_classes,
)
from ml.eval.protocol import (
    EVALUATION_PROTOCOL_VERSION,
    OutOfFoldPrediction,
    OutOfFoldResult,
    evaluation_protocol,
    nested_out_of_fold,
)
from ml.eval.report import (
    ALERT_BUDGET_RECALL,
    GroupRows,
    abstention_breakdown,
    build_evaluation_report,
    core_metrics,
    decision_coverage,
    group_metrics,
    limitations,
)
from ml.prediction.challenger import ChallengerRow
from ml.prediction.landmarks import Landmark
from packages.shared.enums import DataOrigin, IntendedUse, MetricStatus, TrackId
from tests.p1 import train_factories as tf
from tests.p1.factories import ident
from tests.p1.test_train import CUTOFF, SUBJECT_A, SUBJECT_B, _build, _two_class_inputs
from tools.train.evaluate import evaluate_run, evaluation_report_payload
from tools.train.run import run_challenger_training

BOTH_CLASSES = ([1, 0, 1, 0], [0.8, 0.3, 0.6, 0.2])
ONE_CLASS = ([0, 0, 0], [0.2, 0.3, 0.4])


class TestMetrics:
    def test_brier_matches_the_worked_example(self) -> None:
        # FUNDAMENTOS 13.1: y=[1,0], p=[0.8,0.3] gives 0.065.
        assert brier_score([1, 0], [0.8, 0.3]) == pytest.approx(0.065)

    def test_average_precision_is_scikit_learns(self) -> None:
        labels, probabilities = BOTH_CLASSES
        assert average_precision(labels, probabilities) == pytest.approx(
            float(average_precision_score(labels, probabilities))
        )

    def test_a_single_class_produces_no_average_precision_and_no_auc(self) -> None:
        labels, probabilities = ONE_CLASS
        assert not has_both_classes(labels)
        assert average_precision(labels, probabilities) is None
        assert auc_roc(labels, probabilities) is None
        # Brier is defined per row, so it survives a single class.
        assert brier_score(labels, probabilities) is not None

    def test_a_probability_outside_the_unit_interval_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"\[0,1\]"):
            brier_score([1], [1.4])

    def test_calibration_recovers_a_known_intercept_and_slope(self) -> None:
        # Perfectly calibrated predictions give a slope near 1 and an intercept
        # near 0; the check is loose because 200 rows are still noisy.
        import numpy as np

        generator = np.random.default_rng(42)
        probabilities = list(generator.uniform(0.05, 0.95, size=400))
        labels = [int(generator.uniform() < probability) for probability in probabilities]
        fit = calibration_fit(labels, probabilities)
        assert fit.estimable
        assert fit.slope == pytest.approx(1.0, abs=0.45)
        assert fit.intercept == pytest.approx(0.0, abs=0.45)

    def test_calibration_refuses_a_single_class(self) -> None:
        labels, probabilities = ONE_CLASS
        fit = calibration_fit(labels, probabilities)
        assert not fit.estimable
        assert fit.not_estimable_reason == "single_class"


class TestBootstrap:
    def test_the_same_seed_produces_the_same_interval(self) -> None:
        labels = [1, 0, 1, 0, 1, 0]
        probabilities = [0.9, 0.2, 0.7, 0.1, 0.8, 0.3]
        subjects = [SUBJECT_A, SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B, SUBJECT_B]
        first = cluster_bootstrap(
            brier_score,
            labels=labels,
            probabilities=probabilities,
            subject_ids=subjects,
            replicates=200,
        )
        second = cluster_bootstrap(
            brier_score,
            labels=labels,
            probabilities=probabilities,
            subject_ids=subjects,
            replicates=200,
        )
        assert first.estimable
        assert (first.lower, first.upper) == (second.lower, second.upper)

    def test_resampling_is_by_subject_not_by_row(self) -> None:
        # Two subjects give exactly three possible resamples -- both draws of A,
        # one of each, both of B -- so the interval can only span the Brier of
        # A alone and of B alone. Row-level resampling would produce values in
        # between and a visibly narrower interval.
        labels = [1, 1, 0, 0]
        probabilities = [0.9, 0.8, 0.4, 0.3]
        subjects = [SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B]
        result = cluster_bootstrap(
            brier_score,
            labels=labels,
            probabilities=probabilities,
            subject_ids=subjects,
            replicates=300,
        )
        assert result.estimable
        assert result.valid_replicates == 300
        assert result.lower == pytest.approx(brier_score([1, 1], [0.9, 0.8]))
        assert result.upper == pytest.approx(brier_score([0, 0], [0.4, 0.3]))

    def test_too_few_valid_replicates_publishes_no_interval(self) -> None:
        # All of one subject is positive and all of the other negative, so half
        # the subject resamples hold a single class and average precision is
        # undefined on them.
        labels = [1, 1, 0, 0]
        probabilities = [0.9, 0.8, 0.1, 0.2]
        subjects = [SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B]
        result = cluster_bootstrap(
            average_precision,
            labels=labels,
            probabilities=probabilities,
            subject_ids=subjects,
            replicates=200,
        )
        assert not result.estimable
        assert result.not_estimable_reason == "insufficient_valid_bootstrap_replicates"
        assert result.valid_fraction < 0.8

    def test_one_subject_cannot_be_bootstrapped(self) -> None:
        result = cluster_bootstrap(
            brier_score,
            labels=[1, 0],
            probabilities=[0.8, 0.2],
            subject_ids=[SUBJECT_A, SUBJECT_A],
            replicates=50,
        )
        assert not result.estimable
        assert result.not_estimable_reason == "single_subject"


class TestProtocol:
    def test_the_protocol_records_splits_seed_and_estimability_rules(self) -> None:
        protocol = evaluation_protocol()
        assert protocol.protocol_version == EVALUATION_PROTOCOL_VERSION
        assert protocol.outer_split == "LeaveOneGroupOut(subject_id)"
        assert protocol.random_seed == 42
        assert protocol.bootstrap_replicates == 2000
        assert protocol.interval_level == 0.90
        assert protocol.min_valid_bootstrap_fraction == 0.80
        assert (protocol.group_min_subjects, protocol.group_min_positives) == (10, 5)

    def test_changing_the_reveal_schedule_changes_the_protocol_hash(self) -> None:
        outcome = run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:protocol"),
            dataset_snapshot_id=ident("snapshot:protocol"),
            started_at=CUTOFF,
        )
        with_schedule = evaluation_protocol(outcome.reveal_events)
        without = evaluation_protocol()
        assert with_schedule.reveal_schedule_sha256 is not None
        assert with_schedule.content_sha256 != without.content_sha256

    def test_every_landmark_is_predicted_exactly_once(self) -> None:
        outcome = run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:oof"),
            dataset_snapshot_id=ident("snapshot:oof"),
            started_at=CUTOFF,
        )
        result = nested_out_of_fold(outcome.landmarks)
        ids = [item.prediction_episode_id for item in result.predictions]
        assert len(ids) == len(set(ids)) == len(outcome.landmarks)

    def test_the_penalty_is_chosen_inside_each_outer_train(self) -> None:
        outcome = run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:lambda"),
            dataset_snapshot_id=ident("snapshot:lambda"),
            started_at=CUTOFF,
        )
        result = nested_out_of_fold(outcome.landmarks)
        # One selection per held-out subject, never one global fit.
        held_out = {subject_id for subject_id, _ in result.selected_penalties}
        assert held_out == {
            landmark.subject_id for landmark in outcome.landmarks if landmark.is_estimable
        }

    def test_an_outer_fold_with_nothing_left_to_train_on_abstains(self) -> None:
        landmarks = tuple(
            Landmark(
                prediction_episode_id=ident(f"episode:solo-{index}"),
                subject_id=SUBJECT_A,
                as_of_at=CUTOFF - timedelta(days=index + 1),
                source=tf.Source.HOME,
                label=index % 2,
                row=ChallengerRow(
                    subject_id=SUBJECT_A,
                    p_base=0.2,
                    sleep_deviation=0.1,
                    regulation_deviation=-0.1,
                    label=index % 2,
                ),
            )
            for index in range(4)
        )
        # Leaving the only subject out leaves an empty outer train, so the fold
        # reports why rather than predicting from nothing.
        result = nested_out_of_fold(landmarks)
        assert result.estimated == ()
        assert set(result.abstention_counts()) == {"not_trainable_single_class"}


class TestReport:
    def _outcome(self):
        return run_challenger_training(
            _two_class_inputs(),
            training_run_id=ident("run:report"),
            dataset_snapshot_id=ident("snapshot:report"),
            started_at=CUTOFF,
        )

    def test_alert_budget_recall_is_always_not_estimable(self) -> None:
        result = nested_out_of_fold(self._outcome().landmarks)
        metrics = {metric.name: metric for metric in core_metrics(result, with_intervals=False)}
        alert = metrics[ALERT_BUDGET_RECALL]
        assert alert.status is MetricStatus.NOT_ESTIMABLE
        assert alert.not_estimable_reason == "no_decision_policy_version"

    def test_coverage_and_abstentions_share_one_denominator(self) -> None:
        result = nested_out_of_fold(self._outcome().landmarks)
        coverage = decision_coverage(result)
        assert coverage.denominator == len(result.predictions)
        for abstention in abstention_breakdown(result):
            assert abstention.rate == pytest.approx(abstention.count / len(result.predictions))

    def test_a_small_group_is_suppressed_including_its_counts(self) -> None:
        small = GroupRows(
            group_kind="source",
            group_value="school",
            subject_ids=(SUBJECT_A, SUBJECT_B),
            labels=(1, 0),
            probabilities=(0.7, 0.2),
        )
        reported = group_metrics((small,))[0]
        assert reported.suppressed
        assert reported.metrics == ()
        assert (reported.subject_count, reported.positive_count) == (0, 0)

    def test_a_group_meeting_the_minimums_reports_metrics(self) -> None:
        subjects = tuple(tf.subject(f"group-{index}") for index in range(12))
        labels = tuple(1 if index < 6 else 0 for index in range(12))
        probabilities = tuple(0.8 if label else 0.2 for label in labels)
        reported = group_metrics(
            (
                GroupRows(
                    group_kind="care_mode",
                    group_value="standard_support",
                    subject_ids=subjects,
                    labels=labels,
                    probabilities=probabilities,
                ),
            )
        )[0]
        assert not reported.suppressed
        assert reported.subject_count == 12
        assert {metric.name for metric in reported.metrics} == {
            "brier_score",
            "average_precision",
        }

    def test_a_real_report_states_origin_dataset_hash_and_model(self) -> None:
        outcome = self._outcome()
        evaluation = evaluate_run(
            outcome,
            evaluation_report_id=ident("evaluation:real"),
            created_at=CUTOFF,
            with_intervals=False,
        )
        report = evaluation.report
        assert report.data_origin is DataOrigin.REAL
        assert report.dataset_sha256 == outcome.snapshot.content_sha256
        assert report.model_version == outcome.run.model_version
        assert report.target_definition_version == tf.TARGET_VERSION
        assert not report.is_simulation_only

    def test_a_synthetic_report_is_simulation_only(self) -> None:
        outcome = self._outcome()
        synthetic_snapshot = outcome.snapshot.model_copy(
            update={"data_origin": DataOrigin.SYNTHETIC}
        )
        result = nested_out_of_fold(outcome.landmarks)
        report = build_evaluation_report(
            result,
            evaluation_report_id=ident("evaluation:synthetic"),
            snapshot=synthetic_snapshot,
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
                evaluation_report_id=ident("evaluation:mislabelled"),
                snapshot=synthetic_snapshot,
                model_version="synthetic-reference-0.2.1",
                track_id=TrackId.SYNTHETIC_REFERENCE_V021,
                intended_use=IntendedUse.OPERATIONAL_SUPPORT,
                protocol_version=EVALUATION_PROTOCOL_VERSION,
                created_at=CUTOFF,
                with_intervals=False,
            )

    def test_a_single_class_report_falls_back_to_counts_and_completeness(self) -> None:
        result = OutOfFoldResult(
            predictions=(
                OutOfFoldPrediction(ident("e1"), SUBJECT_A, 0, 0.2),
                OutOfFoldPrediction(ident("e2"), SUBJECT_B, 0, 0.3),
            ),
            selected_penalties=(),
        )
        snapshot = _build(_two_class_inputs()).snapshot
        report = build_evaluation_report(
            result,
            evaluation_report_id=ident("evaluation:counts"),
            snapshot=snapshot,
            model_version="real-logit-challenger-0.3.0",
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
            intended_use=IntendedUse.SHADOW_EVALUATION,
            protocol_version=EVALUATION_PROTOCOL_VERSION,
            created_at=CUTOFF,
            with_intervals=False,
        )
        by_name = {metric.name: metric for metric in report.metrics}
        assert by_name["auc_roc"].status is MetricStatus.NOT_ESTIMABLE
        assert by_name["average_precision"].not_estimable_reason == "single_class"
        assert by_name["labelled_episodes"].value == 2.0
        assert by_name["negative_outcomes"].value == 2.0

    def test_limitations_never_use_the_word_efficacy_as_a_claim(self) -> None:
        for line in limitations(data_origin=DataOrigin.REAL):
            assert "no son eficacia" in line or "eficacia" not in line

    def test_the_evaluation_manifest_carries_versions_and_hashes(self, tmp_path: Path) -> None:
        evaluation = evaluate_run(
            self._outcome(),
            evaluation_report_id=ident("evaluation:manifest"),
            created_at=CUTOFF,
            with_intervals=False,
        )
        payload = evaluation_report_payload(evaluation)
        (tmp_path / "evaluation.json").write_text(json.dumps(payload), encoding="utf-8")
        assert payload["protocol_version"] == EVALUATION_PROTOCOL_VERSION
        assert len(payload["protocol_sha256"]) == 64
        assert payload["reveal_schedule_sha256"] is not None
        assert payload["simulation_only"] is False
        assert payload["limitations_es"]
