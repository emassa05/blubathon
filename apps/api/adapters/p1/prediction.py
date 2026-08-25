"""`ml.prediction` detrás del puerto de predicción dual-track (SPEC 8, 11.5).

El puerto pide `predict` y P1 no publica esa façade: publica el doble track
separado, que es lo correcto porque los tres tracks no comparten significado.
El adaptador llama a cada uno y arma la tupla de salidas.

- `synthetic_reference_v021`: `score_simulation`, que rechaza cohorte real y
  origen real antes de calcular. Sin artefacto v0.2 en el repositorio la salida
  es `unavailable` con `model_artifact_unavailable`, nunca un número inventado.
- `real_personal_baseline_v1`: `build_personal_baseline` sobre los episodios
  primarios anteriores del sujeto y sus resoluciones verificadas.
- `real_logit_challenger_v1`: `assess_trainability`, y jamás expuesto (SPEC 8.5).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import parse_timestamp
from apps.api.ports.prediction import TrackOutput
from apps.api.store import history
from apps.api.store.db import Database
from ml.prediction import (
    BASELINE_MODEL_VERSION,
    CHALLENGER_MODEL_VERSION,
    SYNTHETIC_MODEL_VERSION,
    BaselineCandidate,
    build_personal_baseline,
    score_simulation,
)
from ml.prediction.synthetic_reference import CohortViolationError
from packages.shared.enums import (
    CohortKind,
    ConsentPurpose,
    DataOrigin,
    EstimateKind,
    IntendedUse,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
    TrackId,
)
from packages.shared.projection import project_as_of

VERIFIED = frozenset({OutcomeResolutionStatus.YES, OutcomeResolutionStatus.NO})


class P1Prediction:
    """El artefacto de simulación v0.2 no está en Git, así que no se carga."""

    def __init__(self, *, database: Database, artifact: Any | None = None) -> None:
        self._database = database
        self._artifact = artifact

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
        cutoff = parse_timestamp(as_of_at)
        return (
            self._synthetic(cohort_kind, input_data_origin, snapshot),
            self._baseline(
                tenant_id=tenant_id,
                subject_id=subject_id,
                as_of_at=as_of_at,
                cutoff=cutoff,
                care_mode=care_mode,
                target_definition_version=target_definition_version,
                input_data_origin=input_data_origin,
            ),
            self._challenger(tenant_id=tenant_id, input_data_origin=input_data_origin),
        )

    # -- tracks ------------------------------------------------------------

    def _synthetic(
        self, cohort_kind: str, input_data_origin: str, snapshot: dict[str, Any]
    ) -> TrackOutput:
        try:
            result = score_simulation(
                {key: float(value) for key, value in snapshot.items() if _is_number(value)},
                cohort_kind=CohortKind(cohort_kind),
                input_data_origin=DataOrigin(input_data_origin),
                artifact=self._artifact,
            )
        except CohortViolationError:
            # SPEC 2.14 / INV-18: el track de simulación rechaza un sujeto real
            # y una entrada real. La negativa es la salida, no una excepción.
            return TrackOutput(
                track_id=TrackId.SYNTHETIC_REFERENCE_V021.value,
                intended_use=IntendedUse.SIMULATION_ONLY.value,
                status=PredictionStatus.ABSTAINED.value,
                estimate_kind=EstimateKind.SIMULATION_SCORE.value,
                model_version=SYNTHETIC_MODEL_VERSION,
                input_data_origin=input_data_origin,
                abstention_reasons=(PredictionAbstentionReason.COHORT_NOT_ELIGIBLE.value,),
                exposed=False,
            )
        return TrackOutput(
            track_id=TrackId.SYNTHETIC_REFERENCE_V021.value,
            intended_use=result.intended_use.value,
            status=result.status.value,
            estimate_kind=EstimateKind.SIMULATION_SCORE.value,
            model_version=result.model_version,
            input_data_origin=DataOrigin.SYNTHETIC.value,
            simulation_score=result.simulation_score,
            abstention_reasons=tuple(reason.value for reason in result.abstention_reasons),
        )

    def _baseline(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        as_of_at: str,
        cutoff: Any,
        care_mode: str | None,
        target_definition_version: str,
        input_data_origin: str,
    ) -> TrackOutput:
        connection = self._database.connection
        episode_rows = history.previous_primary_episodes(
            connection, tenant_id=tenant_id, subject_id=subject_id, before_at=as_of_at
        )
        episode_ids = tuple(str(row["prediction_episode_id"]) for row in episode_rows)
        resolution_rows = history.resolutions_for_episodes(
            connection, prediction_episode_ids=episode_ids
        )
        resolutions = project_as_of(
            [translate.outcome_resolution(row) for row in resolution_rows], cutoff
        )
        by_episode = {
            resolution.prediction_episode_id: resolution for resolution in resolutions.leaves
        }
        consented = frozenset(
            history.active_consent_subject_ids(
                connection,
                tenant_id=tenant_id,
                purpose=ConsentPurpose.OPERATIONAL_SUPPORT.value,
                cutoff=as_of_at,
            )
        )
        candidates = []
        for row in episode_rows:
            episode = translate.prediction_episode(row)
            resolution = by_episode.get(episode.prediction_episode_id)
            if resolution is None or resolution.status not in VERIFIED:
                continue
            candidates.append(
                BaselineCandidate(
                    episode=episode,
                    resolution=resolution,
                    consent_authorized=str(episode.subject_id) in consented,
                )
            )

        estimate = build_personal_baseline(
            candidates,
            as_of_at=cutoff,
            subject_id=UUID(subject_id),
            care_mode=care_mode,
            target_definition_version=target_definition_version,
        )
        interval = (
            None
            if estimate.interval is None
            else (estimate.interval.lower, estimate.interval.upper)
        )
        return TrackOutput(
            track_id=TrackId.REAL_PERSONAL_BASELINE_V1.value,
            intended_use=IntendedUse.OPERATIONAL_SUPPORT.value,
            status=estimate.status.value,
            estimate_kind=EstimateKind.PERSONAL_OBSERVED_EPISODE_RATE.value,
            model_version=estimate.model_version,
            input_data_origin=input_data_origin,
            probability=estimate.probability,
            interval=interval,
            interval_method=None if interval is None else "beta_posterior_quantile",
            abstention_reasons=tuple(reason.value for reason in estimate.abstention_reasons),
        )

    def _challenger(self, *, tenant_id: str, input_data_origin: str) -> TrackOutput:
        """SPEC 8.4-8.5: el challenger se entrena offline y solo puntúa en sombra.

        En runtime no se entrena nada. Si `tools/train` no publicó una versión en
        estado `shadow`, la razón es exactamente esa; `not_trainable_single_class`
        pertenece a `NotTrainableReason`, que es de entrenamiento y no del
        catálogo cerrado de abstenciones publicadas.
        """
        shadow = history.shadow_model_version(
            self._database.connection,
            tenant_id=tenant_id,
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
        )
        return TrackOutput(
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            intended_use=IntendedUse.SHADOW_EVALUATION.value,
            status=PredictionStatus.ABSTAINED.value,
            estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE.value,
            model_version=(CHALLENGER_MODEL_VERSION if shadow is None else shadow["model_version"]),
            input_data_origin=input_data_origin,
            abstention_reasons=(PredictionAbstentionReason.MODEL_STATE_NOT_SHADOW.value,),
            # SPEC 8.5: en v0.3 el challenger nunca se expone, ni con modelo.
            exposed=False,
        )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


__all__ = ["BASELINE_MODEL_VERSION", "P1Prediction"]
