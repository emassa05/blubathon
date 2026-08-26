"""Children list, profile and daily history views."""

from __future__ import annotations

import sqlite3

from apps.api.contracts.models import (
    ChildHistoryDay,
    ChildHistoryOutcome,
    ChildHistoryPrediction,
    ChildHistoryRecommendation,
    ChildHistoryResponse,
    ChildListItem,
    ChildListResponse,
    ChildView,
)
from apps.api.errors import not_found
from apps.api.services.base import Services
from apps.api.store import form_sessions, history, identity, recommendations


class ChildService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def list(self, connection: sqlite3.Connection, *, tenant_id: str) -> ChildListResponse:
        return ChildListResponse(
            children=[
                ChildListItem(child_id=row["subject_id"], display_label=row["display_label"])
                for row in identity.subjects_for_tenant(connection, tenant_id=tenant_id)
            ]
        )

    def get(
        self, connection: sqlite3.Connection, *, tenant_id: str, child_id: str, now: str
    ) -> ChildView:
        subject = identity.subject(connection, child_id)
        if subject is None or subject["tenant_id"] != tenant_id:
            raise not_found()
        profile = identity.active_profile(
            connection, tenant_id=tenant_id, subject_id=child_id, cutoff=now
        )
        episode = form_sessions.open_primary_episode(
            connection, tenant_id=tenant_id, subject_id=child_id, at=now
        )
        return ChildView(
            child_id=child_id,
            display_label=subject["display_label"],
            sensory_profile_tags=() if profile is None else profile["sensory_profile_tags"],
            communication_support_tags=(
                () if profile is None else profile["communication_support_tags"]
            ),
            contraindication_tags=() if profile is None else profile["contraindication_tags"],
            care_mode=None if profile is None else profile["care_mode"],
            profile_version=None if profile is None else profile["profile_version"],
            prediction_episode_id=(None if episode is None else episode["prediction_episode_id"]),
        )

    def history(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        child_id: str,
        limit: int,
    ) -> ChildHistoryResponse:
        subject = identity.subject(connection, child_id)
        if subject is None or subject["tenant_id"] != tenant_id:
            raise not_found()
        days = []
        for row in history.child_submission_days(
            connection, tenant_id=tenant_id, subject_id=child_id, limit=limit
        ):
            prediction = None
            if row["prediction_status"] is not None:
                status = "ok" if row["prediction_status"] == "ok" else "abstained"
                interval = (
                    None
                    if row["interval_low"] is None or row["interval_high"] is None
                    else (row["interval_low"], row["interval_high"])
                )
                prediction = ChildHistoryPrediction(
                    status=status,
                    probability=row["probability"] if status == "ok" else None,
                    interval=interval if status == "ok" else None,
                )
            recommendation = None
            if row["recommendation_instance_id"] is not None:
                feedback = recommendations.latest_feedback(
                    connection, row["recommendation_instance_id"]
                )
                recommendation = ChildHistoryRecommendation(
                    recommendation_instance_id=row["recommendation_instance_id"],
                    status=row["recommendation_status"],
                    rating=None if feedback is None else feedback["rating"],
                )
            outcome = None
            if row["prediction_episode_id"] is not None:
                outcome = ChildHistoryOutcome(
                    status=row["outcome_status"] or "pending",
                    reported_at=row["outcome_reported_at"],
                )
            days.append(
                ChildHistoryDay(
                    local_date=row["local_date"],
                    submission_id=row["submission_id"],
                    prediction_episode_id=row["prediction_episode_id"],
                    prediction=prediction,
                    recommendation=recommendation,
                    outcome=outcome,
                )
            )
        return ChildHistoryResponse(child_id=child_id, days=days)
