"""Offline snapshots, training runs and their manifests (TAREAS P1.8).

`tools/train` reads already-loaded domain rows, projects them to a cutoff,
re-checks consent at the moment the run starts, and writes manifests. It never
trains inside the API, and it never promotes a model.
"""

from tools.train.consent import (
    ConsentAuthorization,
    authorize_secondary_model_use,
    revocation_impact,
    suspend_dependent_models,
    suspend_dependent_reports,
)
from tools.train.run import (
    CODE_VERSION,
    TrainingOutcome,
    challenger_protocol,
    dependency_versions,
    run_challenger_training,
    run_report,
)
from tools.train.snapshot import (
    DATASET_ARTIFACT,
    SnapshotBuild,
    SnapshotInputs,
    build_dataset_snapshot,
)

__all__ = [
    "CODE_VERSION",
    "DATASET_ARTIFACT",
    "ConsentAuthorization",
    "SnapshotBuild",
    "SnapshotInputs",
    "TrainingOutcome",
    "authorize_secondary_model_use",
    "build_dataset_snapshot",
    "challenger_protocol",
    "dependency_versions",
    "revocation_impact",
    "run_challenger_training",
    "run_report",
    "suspend_dependent_models",
    "suspend_dependent_reports",
]
