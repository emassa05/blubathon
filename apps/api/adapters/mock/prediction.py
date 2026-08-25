"""Predicción fixture (sustituye `ml/prediction` hasta H1).

Este stub no entrena ni estima. Devuelve exactamente lo que el SPEC exige que se
vea con los datos actuales (SPEC 1.2, 8.5, 20.8-20.9):

- `synthetic_reference_v021`: `simulation_score` de fixture, solo sobre cohorte
  `demo_fixture`, con `probability` e `interval` nulos y `intended_use=
  simulation_only`. Un sujeto real lo hace abstenerse (INV-18).
- `real_personal_baseline_v1`: abstención `insufficient_verified_outcomes`,
  porque el repositorio no tiene 5 outcomes verificados (SPEC 8.5 / C19).
- `real_logit_challenger_v1`: abstención `not_trainable_single_class` y nunca
  expuesto (SPEC 8.4, 8.5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api.contracts.enums import (
    CohortKind,
    DataOrigin,
    EstimateKind,
    IntendedUse,
    PredictionStatus,
    TrackId,
)
from apps.api.ports.prediction import TrackOutput

FIXTURES = Path(__file__).resolve().parent / "fixtures"

SYNTHETIC_MODEL_VERSION = "synthetic-reference-mock-0.2.1"
BASELINE_MODEL_VERSION = "personal-baseline-mock-0.3.0"
CHALLENGER_MODEL_VERSION = "logit-challenger-mock-0.3.0"


class MockPrediction:
    def __init__(self) -> None:
        self._scores: dict[str, float] = json.loads(
            (FIXTURES / "simulation_scores.json").read_text(encoding="utf-8")
        )

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
    ) -> tuple[TrackOutput, ...]:
        return (
            self._synthetic(subject_id, cohort_kind, input_data_origin),
            self._baseline(input_data_origin, care_mode),
            self._challenger(input_data_origin),
        )

    def _synthetic(self, subject_id: str, cohort_kind: str, input_data_origin: str) -> TrackOutput:
        is_demo = cohort_kind == CohortKind.DEMO_FIXTURE.value
        if not is_demo:
            # SPEC 2.14 / INV-18: el modelo sintético rechaza sujetos reales.
            return TrackOutput(
                track_id=TrackId.SYNTHETIC_REFERENCE_V021.value,
                intended_use=IntendedUse.SIMULATION_ONLY.value,
                status=PredictionStatus.ABSTAINED.value,
                estimate_kind=EstimateKind.SIMULATION_SCORE.value,
                model_version=SYNTHETIC_MODEL_VERSION,
                input_data_origin=input_data_origin,
                abstention_reasons=("real_subject_rejected_by_simulation_track",),
                exposed=False,
            )
        score = self._scores.get(subject_id)
        if score is None:
            return TrackOutput(
                track_id=TrackId.SYNTHETIC_REFERENCE_V021.value,
                intended_use=IntendedUse.SIMULATION_ONLY.value,
                status=PredictionStatus.ABSTAINED.value,
                estimate_kind=EstimateKind.SIMULATION_SCORE.value,
                model_version=SYNTHETIC_MODEL_VERSION,
                input_data_origin=DataOrigin.SYNTHETIC.value,
                abstention_reasons=("simulation_fixture_unavailable",),
            )
        # SPEC 8.2 y 11.5: score de simulación, sin probabilidad ni intervalo.
        return TrackOutput(
            track_id=TrackId.SYNTHETIC_REFERENCE_V021.value,
            intended_use=IntendedUse.SIMULATION_ONLY.value,
            status=PredictionStatus.OK.value,
            estimate_kind=EstimateKind.SIMULATION_SCORE.value,
            model_version=SYNTHETIC_MODEL_VERSION,
            input_data_origin=DataOrigin.SYNTHETIC.value,
            simulation_score=score,
        )

    def _baseline(self, input_data_origin: str, care_mode: str | None) -> TrackOutput:
        reasons = ["insufficient_verified_outcomes"]
        if care_mode is None:
            reasons.append("care_mode_history_unavailable")
        return TrackOutput(
            track_id=TrackId.REAL_PERSONAL_BASELINE_V1.value,
            intended_use=IntendedUse.OPERATIONAL_SUPPORT.value,
            status=PredictionStatus.ABSTAINED.value,
            estimate_kind=EstimateKind.PERSONAL_OBSERVED_EPISODE_RATE.value,
            model_version=BASELINE_MODEL_VERSION,
            input_data_origin=input_data_origin,
            abstention_reasons=tuple(reasons),
        )

    def _challenger(self, input_data_origin: str) -> TrackOutput:
        return TrackOutput(
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            intended_use=IntendedUse.SHADOW_EVALUATION.value,
            status=PredictionStatus.ABSTAINED.value,
            estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE.value,
            model_version=CHALLENGER_MODEL_VERSION,
            input_data_origin=input_data_origin,
            abstention_reasons=("not_trainable_single_class",),
            # SPEC 8.5: el challenger nunca se expone en v0.3.
            exposed=False,
        )
