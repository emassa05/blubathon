"""The trained artifact and how it is stored (SPEC 9, CONVENTIONS 9).

The dataclass lives here rather than in ``ml/train.py`` on purpose: running
``python -m ml.train`` makes that module ``__main__``, and pickle would record
the class under a name nothing else can resolve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib

from ml.engine.model import RiskEnsemble
from ml.errors import ModelNotReadyError

ARTIFACT_FORMAT = 1


@dataclass
class TrainedModel:
    """A fitted ensemble plus everything the API needs to serve it."""

    ensemble: RiskEnsemble
    evaluation: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def population_prior(self) -> dict[str, dict[str, float]]:
        """SPEC 8.4 cold-start prior, measured on the training split only."""
        return self.ensemble.population_prior_


def save_model(model: TrainedModel, path: Path | str) -> Path:
    """Persist the artifact. Trained models stay out of git (CONVENTIONS 9)."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, destination, compress=3)
    return destination


def load_model(path: Path | str) -> TrainedModel:
    """Load a trained artifact, or say plainly that there is nothing to serve."""
    source = Path(path)
    if not source.exists():
        raise ModelNotReadyError(f"no trained model at {source}; run python -m ml.train")
    model = joblib.load(source)
    if not isinstance(model, TrainedModel) or not model.ensemble.is_fitted:
        raise ModelNotReadyError(f"the artifact at {source} does not hold a fitted ensemble")
    return model
