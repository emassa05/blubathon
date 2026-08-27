"""Puerto de predicción dual-track (SPEC 8, 11.5; P1.5 `ml/prediction`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class TrackOutput:
    """Una salida por track. La abstención es una salida válida, no un error."""

    track_id: str
    intended_use: str
    status: str
    estimate_kind: str
    model_version: str
    input_data_origin: str
    probability: float | None = None
    simulation_score: float | None = None
    interval: tuple[float, float] | None = None
    interval_method: str | None = None
    abstention_reasons: tuple[str, ...] = ()
    # SPEC 8.5: el challenger en sombra guarda score pero nunca se expone.
    exposed: bool = True


class PredictionPort(Protocol):
    def predict(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        prediction_episode_id: str,
        as_of_at: str,
        cohort_kind: str,
        input_data_origin: str,
        care_mode: str | None,
        target_definition_version: str,
        snapshot: dict[str, Any],
    ) -> tuple[TrackOutput, ...]: ...
