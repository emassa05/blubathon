"""The `synthetic_reference_v021` track (SPEC 8.2).

The v0.2 LightGBM model is kept for integration tests, abstention and VoI
demonstrations, leakage and determinism checks, and stress tests. It is not kept
for people. Everything it produces is a `simulation_score` in `[0,1]`, with
`probability` and `interval` null, shown only on `demo_fixture` cohorts and
labelled in the UI as the score of a designed simulation.

The guard is at the top of this module rather than in a caller: a simulation
model must not be able to run on a real subject even by mistake (SPEC 2.14,
INV-18).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from ml.errors import CohortViolationError
from packages.shared.enums import (
    CohortKind,
    DataOrigin,
    IntendedUse,
    PredictionAbstentionReason,
    PredictionStatus,
)

SYNTHETIC_MODEL_VERSION = "synthetic-reference-0.2.1"
SYNTHETIC_TRACK_INTENDED_USE = IntendedUse.SIMULATION_ONLY


class SimulationArtifact(Protocol):
    """A loaded v0.2.1 artifact that scores an already-synthetic feature vector."""

    @property
    def model_version(self) -> str: ...

    def score(self, features: Mapping[str, float]) -> float: ...


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """A simulation score, or the reason there is none."""

    status: PredictionStatus
    simulation_score: float | None = None
    abstention_reasons: tuple[PredictionAbstentionReason, ...] = ()
    model_version: str = SYNTHETIC_MODEL_VERSION
    intended_use: IntendedUse = SYNTHETIC_TRACK_INTENDED_USE

    @property
    def probability(self) -> None:
        """Always `None`. A designed simulation is not a clinical probability."""

        return None


def guard_cohort(*, cohort_kind: CohortKind, input_data_origin: DataOrigin) -> None:
    """Refuse a real subject or real input data before anything is computed."""

    if cohort_kind is not CohortKind.DEMO_FIXTURE:
        raise CohortViolationError(
            "the simulation track only runs on demo_fixture cohorts (SPEC 8.2)"
        )
    if input_data_origin is not DataOrigin.SYNTHETIC:
        raise CohortViolationError("the simulation track never runs on real input data (SPEC 2.14)")


def score_simulation(
    features: Mapping[str, float],
    *,
    cohort_kind: CohortKind,
    input_data_origin: DataOrigin,
    artifact: SimulationArtifact | None,
) -> SimulationResult:
    """Score a synthetic feature vector, or state why no score exists.

    A missing artifact is `unavailable`, not a zero and not a guess. The v0.2
    binary is not in Git (`.gitignore`), so a fresh clone reaches exactly this
    branch until someone builds one locally.
    """

    guard_cohort(cohort_kind=cohort_kind, input_data_origin=input_data_origin)

    if artifact is None:
        return SimulationResult(
            status=PredictionStatus.UNAVAILABLE,
            abstention_reasons=(PredictionAbstentionReason.MODEL_ARTIFACT_UNAVAILABLE,),
        )

    score = float(artifact.score(features))
    if not 0.0 <= score <= 1.0:
        raise ValueError("a simulation score must lie in [0,1]")
    return SimulationResult(
        status=PredictionStatus.OK,
        simulation_score=score,
        model_version=artifact.model_version,
    )
