"""`ml.prediction` detrás del puerto de predicción dual-track.

El puerto pide `predict` y P1 no publica esa façade: publica el doble track
separado, que es lo correcto porque los tres tracks no comparten significado.
El adaptador llama a cada uno y arma la tupla de salidas.

- `synthetic_reference_v021`: `score_simulation`, que rechaza cohorte real y
  origen real antes de calcular. Sin artefacto v0.2 en el repositorio la salida
  es `unavailable` con `model_artifact_unavailable`, nunca un número inventado.
- `real_personal_baseline_v1`: `build_personal_baseline` sobre los episodios
  primarios anteriores del sujeto y sus resoluciones verificadas.
- `real_logit_challenger_v1`: `assess_trainability`, y jamás expuesto.
"""

from __future__ import annotations

import json
from datetime import timedelta
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
from ml.prediction.challenger import (
    ChallengerFit,
    ChallengerRow,
    predictor_deviations,
)
from ml.prediction.synthetic_reference import CohortViolationError
from ml.spec_constants import PERSONAL_DEVIATION_WINDOW_DAYS
from packages.shared.enums import (
    CohortKind,
    DataOrigin,
    EstimateKind,
    FieldCode,
    IntendedUse,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
    Source,
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
        baseline = self._baseline(
            tenant_id=tenant_id,
            subject_id=subject_id,
            as_of_at=as_of_at,
            cutoff=cutoff,
            care_mode=care_mode,
            target_definition_version=target_definition_version,
            input_data_origin=input_data_origin,
        )
        return (
            self._synthetic(cohort_kind, input_data_origin, snapshot),
            baseline,
            # El challenger corrige la tasa base, asi que la recibe ya calculada
            # en vez de volver a pedirla.
            self._challenger(
                tenant_id=tenant_id,
                subject_id=subject_id,
                as_of_at=as_of_at,
                cutoff=cutoff,
                input_data_origin=input_data_origin,
                baseline=baseline,
            ),
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
                    consent_authorized=True,
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

    def _challenger(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        as_of_at: str,
        cutoff: Any,
        input_data_origin: str,
        baseline: TrackOutput,
    ) -> TrackOutput:
        """La tasa base personal corregida por el día que se declara.

            logit(p) = logit(p_base) + b0 + b1*desv_sueno + b2*desv_regulacion

        En runtime no se entrena nada: los coeficientes salen del artefacto que
        `tools/train` publicó en estado `shadow`. Las desviaciones se construyen
        con `predictor_deviations`, la misma funcion que uso el entrenamiento,
        porque aplicar el modelo a features distintas de las que vio daria un
        numero con toda la apariencia de ser correcto.

        Cada pieza que falte es una abstencion con su motivo, nunca un numero
        inventado: sin modelo, sin tasa base o sin historia suficiente del
        predictor, el track se calla y la pantalla cae a la tasa base.
        """

        shadow = history.shadow_model_version(
            self._database.connection,
            tenant_id=tenant_id,
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
        )
        if shadow is None or not shadow["artifact"]:
            return self._challenger_abstains(
                input_data_origin,
                CHALLENGER_MODEL_VERSION if shadow is None else shadow["model_version"],
                PredictionAbstentionReason.MODEL_STATE_NOT_SHADOW,
            )

        fit = _fit_from_artifact(shadow["artifact"])
        if fit is None:
            return self._challenger_abstains(
                input_data_origin,
                shadow["model_version"],
                PredictionAbstentionReason.MODEL_STATE_NOT_SHADOW,
            )

        # El offset del challenger es la tasa base: sin ella no hay nada que
        # corregir, y sus propios motivos ya explican por que falta.
        if baseline.probability is None:
            return self._challenger_abstains(
                input_data_origin,
                shadow["model_version"],
                PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES,
            )

        since = (cutoff.date() - timedelta(days=PERSONAL_DEVIATION_WINDOW_DAYS)).isoformat()
        observations = [
            translate.field_observation(row)
            for row in history.observations_for_subject(
                self._database.connection,
                tenant_id=tenant_id,
                subject_id=subject_id,
                since_local_date=since,
            )
        ]
        deviations = predictor_deviations(
            observations,
            tenant_id=UUID(tenant_id),
            subject_id=UUID(subject_id),
            source=Source.HOME,
            as_of_at=cutoff,
        )
        if any(value is None for value in deviations.values()):
            return self._challenger_abstains(
                input_data_origin,
                shadow["model_version"],
                PredictionAbstentionReason.PERSONAL_PREDICTOR_HISTORY_INSUFFICIENT,
            )

        probability = fit.predict(
            ChallengerRow(
                subject_id=UUID(subject_id),
                p_base=baseline.probability,
                sleep_deviation=deviations[FieldCode.SLEEP_QUALITY],
                regulation_deviation=deviations[FieldCode.DAILY_REGULATION_STATE],
                label=0,
            )
        )
        if probability is None:
            return self._challenger_abstains(
                input_data_origin,
                shadow["model_version"],
                PredictionAbstentionReason.MODEL_STATE_NOT_SHADOW,
            )
        return TrackOutput(
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            intended_use=IntendedUse.OPERATIONAL_SUPPORT.value,
            status=PredictionStatus.OK.value,
            estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE.value,
            model_version=shadow["model_version"],
            input_data_origin=input_data_origin,
            probability=probability,
            exposed=True,
        )

    def _challenger_abstains(
        self,
        input_data_origin: str,
        model_version: str,
        reason: PredictionAbstentionReason,
    ) -> TrackOutput:
        return TrackOutput(
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            intended_use=IntendedUse.OPERATIONAL_SUPPORT.value,
            status=PredictionStatus.ABSTAINED.value,
            estimate_kind=EstimateKind.SHADOW_CHALLENGER_SCORE.value,
            model_version=model_version,
            input_data_origin=input_data_origin,
            abstention_reasons=(reason.value,),
            exposed=True,
        )


def _fit_from_artifact(artifact: str) -> ChallengerFit | None:
    """Los coeficientes tal y como `tools/train` los serializo."""

    try:
        payload = json.loads(artifact)
    except json.JSONDecodeError:
        return None
    if payload.get("intercept") is None:
        return None
    return ChallengerFit(
        converged=True,
        intercept=float(payload["intercept"]),
        beta_sleep=None if payload.get("beta_sleep") is None else float(payload["beta_sleep"]),
        beta_regulation=(
            None if payload.get("beta_regulation") is None else float(payload["beta_regulation"])
        ),
        penalty=None if payload.get("penalty") is None else float(payload["penalty"]),
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


__all__ = ["BASELINE_MODEL_VERSION", "P1Prediction"]
