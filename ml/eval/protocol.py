"""The versioned development protocol: nested LOGO, out of fold once (SPEC 14.4).

The outer loop is `LeaveOneGroupOut(subject_id)` and predicts each episode
exactly once. Inside each outer training set, an inner `LeaveOneGroupOut` picks
`lambda` by out-of-fold Brier; the model is then refitted on the whole outer
train and used to predict the held-out subject.

No outer outcome, present or future, participates in a fit or in the selection.
The features of an outer landmark come from that subject's own history revealed
before its cutoff, which is exactly how the model would work in use, and the
reveal schedule hash is persisted with the protocol so that claim is checkable.

These are development results. They never move a model to `shadow_evaluated`:
that needs a preregistered prospective period on a separate dataset.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy
import scipy
import sklearn

from ml.prediction.challenger import ChallengerRow, fit_challenger, select_penalty
from ml.prediction.landmarks import Landmark, RevealEvent, reveal_schedule_sha256
from ml.spec_constants import (
    EVAL_BOOTSTRAP_REPLICATES,
    EVAL_INTERVAL_LEVEL,
    EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
    GROUP_METRIC_MIN_NEGATIVES,
    GROUP_METRIC_MIN_POSITIVES,
    GROUP_METRIC_MIN_SUBJECTS,
    OFFLINE_RANDOM_SEED,
)
from packages.shared.canonical import content_hash
from packages.shared.domain.evaluation import EvaluationProtocolVersion

EVALUATION_PROTOCOL_VERSION = "eval-protocol-0.3.0"
PROTOCOL_ARTIFACT = "evaluation_protocol"

OUTER_SPLIT = "LeaveOneGroupOut(subject_id)"
INNER_SPLIT = "LeaveOneGroupOut(subject_id) within each outer train"


def library_versions() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
    }


def evaluation_protocol(
    reveal_events: Sequence[RevealEvent] = (),
) -> EvaluationProtocolVersion:
    """Splits, seed, interval method and estimability rules, hashed together."""

    schedule_hash = reveal_schedule_sha256(reveal_events) if reveal_events else None
    payload = {
        "protocol_version": EVALUATION_PROTOCOL_VERSION,
        "outer_split": OUTER_SPLIT,
        "inner_split": INNER_SPLIT,
        "random_seed": OFFLINE_RANDOM_SEED,
        "bootstrap_replicates": EVAL_BOOTSTRAP_REPLICATES,
        "interval_level": EVAL_INTERVAL_LEVEL,
        "min_valid_bootstrap_fraction": EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
        "group_min_subjects": GROUP_METRIC_MIN_SUBJECTS,
        "group_min_positives": GROUP_METRIC_MIN_POSITIVES,
        "group_min_negatives": GROUP_METRIC_MIN_NEGATIVES,
        "library_versions": library_versions(),
        "reveal_schedule_sha256": schedule_hash,
    }
    return EvaluationProtocolVersion(
        protocol_version=EVALUATION_PROTOCOL_VERSION,
        outer_split=OUTER_SPLIT,
        inner_split=INNER_SPLIT,
        random_seed=OFFLINE_RANDOM_SEED,
        bootstrap_replicates=EVAL_BOOTSTRAP_REPLICATES,
        interval_level=EVAL_INTERVAL_LEVEL,
        min_valid_bootstrap_fraction=EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
        group_min_subjects=GROUP_METRIC_MIN_SUBJECTS,
        group_min_positives=GROUP_METRIC_MIN_POSITIVES,
        group_min_negatives=GROUP_METRIC_MIN_NEGATIVES,
        library_versions=payload["library_versions"],
        reveal_schedule_sha256=schedule_hash,
        content_sha256=content_hash(PROTOCOL_ARTIFACT, EVALUATION_PROTOCOL_VERSION, payload),
    )


@dataclass(frozen=True, slots=True)
class OutOfFoldPrediction:
    """One outer prediction, or the reason its fold produced none."""

    prediction_episode_id: UUID
    subject_id: UUID
    label: int
    probability: float | None = None
    not_estimable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OutOfFoldResult:
    """Every outer prediction plus the penalties each outer fold selected."""

    predictions: tuple[OutOfFoldPrediction, ...]
    selected_penalties: tuple[tuple[UUID, float | None], ...]

    @property
    def estimated(self) -> tuple[OutOfFoldPrediction, ...]:
        return tuple(item for item in self.predictions if item.probability is not None)

    @property
    def labels(self) -> tuple[int, ...]:
        return tuple(item.label for item in self.estimated)

    @property
    def probabilities(self) -> tuple[float, ...]:
        return tuple(item.probability for item in self.estimated if item.probability is not None)

    @property
    def subject_ids(self) -> tuple[UUID, ...]:
        return tuple(item.subject_id for item in self.estimated)

    @property
    def coverage(self) -> float:
        return len(self.estimated) / len(self.predictions) if self.predictions else 0.0

    def abstention_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.predictions:
            if item.probability is None:
                reason = item.not_estimable_reason or "not_estimable"
                counts[reason] = counts.get(reason, 0) + 1
        return counts


def nested_out_of_fold(landmarks: Iterable[Landmark]) -> OutOfFoldResult:
    """Predict every landmark once, choosing `lambda` only inside its outer train."""

    ordered = tuple(landmarks)
    estimable = [landmark for landmark in ordered if landmark.row is not None]
    rows_by_episode: dict[UUID, ChallengerRow] = {
        landmark.prediction_episode_id: landmark.row
        for landmark in estimable
        if landmark.row is not None
    }
    subjects = sorted({landmark.subject_id for landmark in estimable}, key=str)

    predictions: dict[UUID, OutOfFoldPrediction] = {}
    penalties: list[tuple[UUID, float | None]] = []

    for landmark in ordered:
        if landmark.row is None:
            predictions[landmark.prediction_episode_id] = OutOfFoldPrediction(
                prediction_episode_id=landmark.prediction_episode_id,
                subject_id=landmark.subject_id,
                label=landmark.label,
                not_estimable_reason=landmark.not_estimable_reason or "landmark_not_estimable",
            )

    for held_out in subjects:
        outer_train = [
            rows_by_episode[landmark.prediction_episode_id]
            for landmark in estimable
            if landmark.subject_id != held_out
        ]
        outer_test = [landmark for landmark in estimable if landmark.subject_id == held_out]

        selection = select_penalty(outer_train)
        if selection.penalty is None:
            penalties.append((held_out, None))
            for landmark in outer_test:
                predictions[landmark.prediction_episode_id] = OutOfFoldPrediction(
                    prediction_episode_id=landmark.prediction_episode_id,
                    subject_id=landmark.subject_id,
                    label=landmark.label,
                    not_estimable_reason=(
                        selection.reason.value if selection.reason is not None else "not_estimable"
                    ),
                )
            continue

        fit = fit_challenger(outer_train, penalty=selection.penalty)
        penalties.append((held_out, selection.penalty if fit.converged else None))
        for landmark in outer_test:
            row = rows_by_episode[landmark.prediction_episode_id]
            probability = fit.predict(row)
            predictions[landmark.prediction_episode_id] = OutOfFoldPrediction(
                prediction_episode_id=landmark.prediction_episode_id,
                subject_id=landmark.subject_id,
                label=landmark.label,
                probability=probability,
                not_estimable_reason=None if probability is not None else "convergence_failure",
            )

    return OutOfFoldResult(
        predictions=tuple(predictions[landmark.prediction_episode_id] for landmark in ordered),
        selected_penalties=tuple(penalties),
    )
