"""Train the risk ensemble offline and store it with its evaluation.

Training twenty gradient-boosted models and scoring the full SPEC 13 report
takes minutes, so it happens once here rather than on the first request. The
API loads the artifact at start-up and refuses to guess without it.

Run it after generating the dataset::

    python -m ml.synth.generate --output-dir data
    python -m ml.train --data-dir data --output data/model.joblib
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml.artifact import ARTIFACT_FORMAT, TrainedModel, load_model, save_model
from ml.engine.model import RiskEnsemble, build_supervised_dataset
from ml.errors import ContractViolationError
from ml.eval.report import build_report
from ml.spec_constants import MODEL_VERSION, RANDOM_SEED, SPEC_VERSION
from ml.synth.generate import generate_synthetic_data


def train(
    logs: pd.DataFrame,
    ground_truth: pd.DataFrame | None = None,
    *,
    evaluate: bool = True,
    misspecification: bool = True,
) -> TrainedModel:
    """Fit the ensemble on a log table and score it on the held-out children."""
    supervised = build_supervised_dataset(logs)
    ensemble = RiskEnsemble().fit(supervised.features, supervised.target, supervised.child_ids)
    evaluation: dict[str, Any] = {}
    if evaluate:
        if ground_truth is None:
            raise ContractViolationError("evaluation needs the generator's ground truth")
        evaluation = build_report(
            ensemble,
            logs,
            ground_truth,
            supervised,
            generate=generate_synthetic_data if misspecification else None,
        )
    return TrainedModel(
        ensemble=ensemble,
        evaluation=evaluation,
        manifest={
            "artifact_format": ARTIFACT_FORMAT,
            "model_version": MODEL_VERSION,
            "spec_version": SPEC_VERSION,
            "seed": RANDOM_SEED,
            "n_children": int(logs["child_id"].nunique()),
            "n_rows": len(supervised.features),
            "n_features": len(ensemble.feature_names_),
            "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Faro risk ensemble")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("data") / "model.joblib")
    parser.add_argument(
        "--skip-misspecification",
        action="store_true",
        help="skip SPEC 13.2, which regenerates three perturbed datasets",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logs_path = args.data_dir / "logs.parquet"
    truth_path = args.data_dir / "ground_truth.parquet"
    if not logs_path.exists():
        raise SystemExit(f"missing {logs_path}; run python -m ml.synth.generate first")
    model = train(
        pd.read_parquet(logs_path),
        pd.read_parquet(truth_path),
        misspecification=not args.skip_misspecification,
    )
    destination = save_model(model, args.output)
    metrics = model.evaluation.get("metrics", {})
    print(f"model -> {destination}")
    print(f"  children={model.manifest['n_children']} features={model.manifest['n_features']}")
    print(f"  auc_pr={metrics.get('auc_pr')} auc_roc={metrics.get('auc_roc')}")
    print(f"  brier={metrics.get('brier')} ece={metrics.get('ece')}")


if __name__ == "__main__":
    main()


__all__ = ["TrainedModel", "load_model", "save_model", "train"]
