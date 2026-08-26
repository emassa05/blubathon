"""Prediction episode reads for the fixed tenant."""

from __future__ import annotations

import sqlite3

from apps.api.contracts.models import PredictionEpisodeView, PredictionOutputView
from apps.api.errors import not_found
from apps.api.services.base import Services
from apps.api.store import episodes as episodes_store
from apps.api.store import outcomes as outcomes_store
from packages.shared.domain.base import Interval


class EpisodeService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def get(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        prediction_episode_id: str,
        now: str,
    ) -> PredictionEpisodeView:
        episode = episodes_store.episode(connection, prediction_episode_id)
        if episode is None or episode["tenant_id"] != tenant_id:
            raise not_found()

        outputs = [
            PredictionOutputView(
                track_id=row["track_id"],
                intended_use=row["intended_use"],
                status=row["status"],
                estimate_kind=row["estimate_kind"],
                probability=row["probability"],
                simulation_score=row["simulation_score"],
                interval=(
                    None
                    if row["interval_low"] is None
                    else Interval(lower=row["interval_low"], upper=row["interval_high"])
                ),
                interval_method=row["interval_method"],
                abstention_reasons=list(row["abstention_reasons"]),
                model_version=row["model_version"],
                input_data_origin=row["input_data_origin"],
            )
            for row in episodes_store.exposed_outputs(connection, prediction_episode_id)
        ]

        request_row = outcomes_store.outcome_request(connection, prediction_episode_id)
        outcome_state = None
        resolution_status = None
        if request_row is not None:
            resolution = outcomes_store.materialize_resolution(
                connection,
                tenant_id=tenant_id,
                prediction_episode_id=prediction_episode_id,
                target_start_at=episode["target_start_at"],
                target_end_at=episode["target_end_at"],
                capture_deadline_at=episode["capture_deadline_at"],
                now=now,
            )
            if resolution is not None:
                resolution_status = resolution["status"]
                outcome_state = outcomes_store.derive_request_status(
                    resolution_status=resolution["status"],
                    capture_deadline_at=request_row["capture_deadline_at"],
                    now=now,
                ).value

        return PredictionEpisodeView(
            prediction_episode_id=episode["prediction_episode_id"],
            subject_id=episode["subject_id"],
            as_of_at=episode["as_of_at"],
            prediction_at=episode["prediction_at"],
            target_start_at=episode["target_start_at"],
            target_end_at=episode["target_end_at"],
            capture_deadline_at=episode["capture_deadline_at"],
            target_definition_version=episode["target_definition_version"],
            outputs=outputs,
            outcome_state=outcome_state,
            resolution_status=resolution_status,
        )
