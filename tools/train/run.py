"""A training run: reauthorise, snapshot, fit or refuse, never promote.

SPEC 10.5 and TAREAS P1.8. The run records what it read (dataset hash, code,
configuration, dependencies), re-checks consent at the moment it starts, and
produces either a candidate `ModelVersion` or an honest `not_trainable` reason.

Promotion does not exist here. A challenger that trains is a candidate, and it
stays in shadow for the whole of v0.3 (SPEC 8.1, C37). With the outcomes the
repository holds today the expected result is `not_trainable_single_class`, and
that is a result, not a failure.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

import numpy
import scipy
import sklearn

from ml.prediction.challenger import (
    CHALLENGER_MODEL_VERSION,
    CHALLENGER_PROTOCOL_VERSION,
    MAX_ITERATIONS,
    OPTIMIZER,
    TOLERANCE,
    ChallengerTrainingResult,
    train_challenger,
)
from ml.prediction.landmarks import (
    Landmark,
    RevealEvent,
    build_landmarks,
    estimable_rows,
    reveal_schedule,
    reveal_schedule_sha256,
)
from ml.spec_constants import CHALLENGER_L2_GRID, CHALLENGER_TIE_TOLERANCE
from packages.shared.canonical import content_hash
from packages.shared.domain.evaluation import (
    ChallengerTrainingProtocolVersion,
    DatasetSnapshot,
    ModelVersion,
    TrainingRun,
)
from packages.shared.enums import (
    DataOrigin,
    IntendedUse,
    ModelState,
    NotTrainableReason,
    Source,
    TrackId,
    TrainingRunStatus,
)
from tools.train.consent import ConsentAuthorization, authorize_secondary_model_use
from tools.train.snapshot import SnapshotBuild, SnapshotInputs, build_dataset_snapshot

CODE_VERSION: Final = "faro-train-0.3.0"
PROTOCOL_ARTIFACT: Final = "challenger_training_protocol"


def dependency_versions() -> dict[str, str]:
    """The library versions a run is reproducible against."""

    return {
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
    }


def challenger_protocol() -> ChallengerTrainingProtocolVersion:
    """Optimiser settings fixed before the run and hashed into it (SPEC 8.4)."""

    payload = {
        "protocol_version": CHALLENGER_PROTOCOL_VERSION,
        "optimizer": OPTIMIZER,
        "tolerance": TOLERANCE,
        "max_iterations": MAX_ITERATIONS,
        "l2_grid": list(CHALLENGER_L2_GRID),
        "tie_tolerance": CHALLENGER_TIE_TOLERANCE,
        "library_versions": dependency_versions(),
    }
    return ChallengerTrainingProtocolVersion(
        protocol_version=CHALLENGER_PROTOCOL_VERSION,
        optimizer=OPTIMIZER,
        tolerance=TOLERANCE,
        max_iterations=MAX_ITERATIONS,
        l2_grid=CHALLENGER_L2_GRID,
        tie_tolerance=CHALLENGER_TIE_TOLERANCE,
        library_versions=payload["library_versions"],
        content_sha256=content_hash(PROTOCOL_ARTIFACT, CHALLENGER_PROTOCOL_VERSION, payload),
    )


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    """Everything one run produced, including the reason it produced no model."""

    run: TrainingRun
    snapshot: DatasetSnapshot
    protocol: ChallengerTrainingProtocolVersion
    landmarks: tuple[Landmark, ...] = ()
    reveal_events: tuple[RevealEvent, ...] = ()
    result: ChallengerTrainingResult | None = None
    model: ModelVersion | None = None
    authorization: ConsentAuthorization | None = None

    @property
    def promoted(self) -> bool:
        """Always false. There is no automatic promotion in v0.3."""

        return False


def _blocked_run(
    *,
    training_run_id: UUID,
    inputs: SnapshotInputs,
    snapshot: DatasetSnapshot,
    protocol: ChallengerTrainingProtocolVersion,
    started_at: datetime,
    reason: NotTrainableReason,
    consent_reauthorized: bool,
) -> TrainingRun:
    return TrainingRun(
        training_run_id=training_run_id,
        tenant_id=inputs.tenant_id,
        dataset_snapshot_id=snapshot.dataset_snapshot_id,
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        status=TrainingRunStatus.NOT_TRAINABLE,
        not_trainable_reason=reason,
        challenger_protocol_version=protocol.protocol_version,
        code_version=CODE_VERSION,
        dependency_versions=dependency_versions(),
        dataset_sha256=snapshot.content_sha256,
        consent_reauthorized=consent_reauthorized,
        started_at=started_at,
        finished_at=started_at,
    )


def run_challenger_training(
    inputs: SnapshotInputs,
    *,
    training_run_id: UUID,
    dataset_snapshot_id: UUID,
    started_at: datetime,
    source: Source = Source.HOME,
) -> TrainingOutcome:
    """Build the snapshot, reauthorise consent, then fit or refuse."""

    if inputs.data_origin is not DataOrigin.REAL:
        raise ValueError("the challenger trains on real outcomes only (SPEC 8.1)")

    build: SnapshotBuild = build_dataset_snapshot(
        inputs, dataset_snapshot_id=dataset_snapshot_id, created_at=started_at
    )
    snapshot = build.snapshot
    protocol = challenger_protocol()

    # SPEC 13.2: the snapshot is immutable for audit, but a run over it starts by
    # asking again, at this instant, for every subject it contains.
    authorization = authorize_secondary_model_use(
        inputs.consents, subject_ids=build.subject_ids, at=started_at
    )
    if authorization.blocks_the_run:
        return TrainingOutcome(
            run=_blocked_run(
                training_run_id=training_run_id,
                inputs=inputs,
                snapshot=snapshot,
                protocol=protocol,
                started_at=started_at,
                reason=NotTrainableReason.CONSENT_NOT_REAUTHORIZED,
                consent_reauthorized=False,
            ),
            snapshot=snapshot,
            protocol=protocol,
            authorization=authorization,
        )

    landmarks = build_landmarks(
        episodes=build.episodes,
        resolutions=build.resolutions,
        observations=build.observations,
        consented_subject_ids=frozenset(build.subject_ids),
        target_definition_version=inputs.target_definition_version,
        source=source,
    )
    reveals = reveal_schedule(build.episodes, build.resolutions)
    result = train_challenger(estimable_rows(landmarks))

    if not result.trainable:
        return TrainingOutcome(
            run=_blocked_run(
                training_run_id=training_run_id,
                inputs=inputs,
                snapshot=snapshot,
                protocol=protocol,
                started_at=started_at,
                reason=result.reason or NotTrainableReason.SINGLE_CLASS,
                consent_reauthorized=True,
            ),
            snapshot=snapshot,
            protocol=protocol,
            landmarks=landmarks,
            reveal_events=reveals,
            result=result,
            authorization=authorization,
        )

    model = ModelVersion(
        model_version=CHALLENGER_MODEL_VERSION,
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        training_run_id=training_run_id,
        training_data_origin=DataOrigin.REAL,
        intended_use=IntendedUse.SHADOW_EVALUATION,
        # A run produces a candidate. Nothing here moves it to shadow, and
        # development out-of-fold results never reach `shadow_evaluated`.
        state=ModelState.CANDIDATE,
        created_at=started_at,
    )
    run = TrainingRun(
        training_run_id=training_run_id,
        tenant_id=inputs.tenant_id,
        dataset_snapshot_id=snapshot.dataset_snapshot_id,
        track_id=TrackId.REAL_LOGIT_CHALLENGER_V1,
        status=TrainingRunStatus.COMPLETED,
        challenger_protocol_version=protocol.protocol_version,
        code_version=CODE_VERSION,
        dependency_versions=dependency_versions(),
        dataset_sha256=snapshot.content_sha256,
        consent_reauthorized=True,
        started_at=started_at,
        finished_at=started_at,
        model_version=model.model_version,
    )
    return TrainingOutcome(
        run=run,
        snapshot=snapshot,
        protocol=protocol,
        landmarks=landmarks,
        reveal_events=reveals,
        result=result,
        model=model,
        authorization=authorization,
    )


def run_report(outcome: TrainingOutcome) -> dict[str, object]:
    """A non-identifiable summary, the shape the CLI writes and P2 imports."""

    return {
        "training_run_id": str(outcome.run.training_run_id),
        "status": outcome.run.status.value,
        "not_trainable_reason": (
            outcome.run.not_trainable_reason.value
            if outcome.run.not_trainable_reason is not None
            else None
        ),
        "track_id": outcome.run.track_id.value,
        "consent_reauthorized": outcome.run.consent_reauthorized,
        "dataset_snapshot_id": str(outcome.snapshot.dataset_snapshot_id),
        "dataset_sha256": outcome.snapshot.content_sha256,
        "data_origin": outcome.snapshot.data_origin.value,
        "target_definition_version": outcome.snapshot.target_definition_version,
        "subject_count": outcome.snapshot.subject_count,
        "positive_count": outcome.snapshot.positive_count,
        "negative_count": outcome.snapshot.negative_count,
        "estimable_landmarks": sum(1 for item in outcome.landmarks if item.is_estimable),
        "not_estimable_landmarks": sorted(
            {item.not_estimable_reason for item in outcome.landmarks if not item.is_estimable}
            - {None}
        ),
        "challenger_protocol_version": outcome.protocol.protocol_version,
        "challenger_protocol_sha256": outcome.protocol.content_sha256,
        "code_version": outcome.run.code_version,
        "dependency_versions": outcome.run.dependency_versions,
        "model_version": outcome.run.model_version,
        "model_state": outcome.model.state.value if outcome.model is not None else None,
        "promoted": outcome.promoted,
        "reveal_event_count": len(outcome.reveal_events),
        "reveal_schedule_sha256": reveal_schedule_sha256(outcome.reveal_events),
    }
