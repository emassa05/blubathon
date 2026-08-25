"""Instancia, inbox, revisión, plan humano y ejecución.

Cubre INV-27, INV-28 y INV-29 desde el flujo API, y la precedencia de
disponibilidad de `SPEC 9.6`.
"""

from __future__ import annotations

import pytest

from tests.p2.test_episodes_and_outcomes import complete_session
from tests.p2.test_form_sessions import open_session
from tools.seed import ids


@pytest.fixture
def catalog_profile() -> str:
    """Este módulo recorre el flujo profesional con el catálogo fixture."""
    return "fixture-active"


def episode_with_recommendations(caregiver):
    result = complete_session(caregiver)
    return result["prediction_episode_id"]


def test_matched_instance_is_persisted_once_with_the_episode(caregiver, db) -> None:
    episode_id = episode_with_recommendations(caregiver)
    rows = db.connection.execute(
        "SELECT * FROM recommendation_instances WHERE prediction_episode_id = ?",
        (episode_id,),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["runtime_status"] == "matched"
    assert rows[0]["availability_reason"] == "ready"
    assert rows[0]["catalog_version"] == ids.CATALOG_FIXTURE


def test_get_recommendations_creates_no_rows(caregiver, professional, db) -> None:
    """CONVENTIONS 12.1: un GET no crea instancias ni solicitudes de autoría."""
    episode_id = episode_with_recommendations(caregiver)

    def counts() -> tuple[int, int]:
        instances = db.connection.execute(
            "SELECT COUNT(*) AS n FROM recommendation_instances"
        ).fetchone()["n"]
        requests = db.connection.execute("SELECT COUNT(*) AS n FROM authoring_requests").fetchone()[
            "n"
        ]
        return instances, requests

    before = counts()
    for _ in range(3):
        professional.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations")
        caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations")
    assert counts() == before


def test_repeated_get_returns_the_same_persisted_envelope(professional, caregiver) -> None:
    episode_id = episode_with_recommendations(caregiver)
    first = professional.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    second = professional.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    assert first == second
    assert first["status"] == "matched"
    assert [item["strategy_version_id"] for item in first["items"]]


def test_caregiver_sees_nothing_until_a_professional_approves(caregiver, professional) -> None:
    """SPEC 11.6: mientras todo esté pending, `awaiting_professional_review`."""
    episode_id = episode_with_recommendations(caregiver)
    view = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    assert view["status"] == "awaiting_professional_review"
    assert view["items"] == []

    inbox = professional.get("/api/v1/recommendation-instances", review_status="pending").json()
    instance = inbox["items"][0]
    strategy_version_id = instance["pending_strategy_version_ids"][0]
    approved = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        {"strategy_version_id": strategy_version_id, "decision": "approved"},
        if_match=instance["revision"],
    )
    assert approved.status_code == 201, approved.text

    view = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    assert view["status"] == "matched"
    assert [item["strategy_version_id"] for item in view["items"]] == [strategy_version_id]
    assert view["items"][0]["citations"], "una estrategia activa trae sus citas"


def test_caregiver_never_sees_a_rejected_or_deferred_strategy(caregiver, professional) -> None:
    episode_id = episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    for strategy_version_id, decision in zip(
        instance["pending_strategy_version_ids"], ("rejected", "deferred"), strict=False
    ):
        revision = professional.get(
            f"/api/v1/prediction-episodes/{episode_id}/recommendations"
        ).json()["revision"]
        response = professional.post(
            f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
            {"strategy_version_id": strategy_version_id, "decision": decision},
            if_match=revision,
        )
        assert response.status_code == 201, response.text
    view = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    assert view["status"] == "awaiting_professional_review"
    assert view["items"] == []


def test_human_plan_replaces_the_strategy_without_rag_citations(caregiver, professional) -> None:
    """INV-29: un plan humano no muestra citas del RAG."""
    episode_id = episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    strategy_version_id = instance["pending_strategy_version_ids"][0]
    response = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        {
            "strategy_version_id": strategy_version_id,
            "decision": "human_plan_substituted",
            "human_plan": {
                "action_text_es": "Acordamos con la familia un plan propio para hoy.",
                "allowed_executor_roles": ["caregiver"],
            },
        },
        if_match=instance["revision"],
    )
    assert response.status_code == 201, response.text
    view = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()
    item = next(item for item in view["items"] if item["item_type"] == "human_plan")
    assert item["citations"] == []
    assert item["action_text_es"] == "Acordamos con la familia un plan propio para hoy."
    assert item["allowed_executor_roles"] == ["caregiver"]


def test_human_plan_cannot_widen_executor_roles(caregiver, professional) -> None:
    episode_id = episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    response = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        {
            "strategy_version_id": instance["pending_strategy_version_ids"][0],
            "decision": "human_plan_substituted",
            "human_plan": {
                "action_text_es": "Plan propio.",
                "allowed_executor_roles": ["caregiver", "tenant_admin"],
            },
        },
        if_match=instance["revision"],
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "human_plan_roles_not_subset"
    assert episode_id


def test_review_requires_if_match_and_rejects_a_stale_revision(caregiver, professional) -> None:
    episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    body = {
        "strategy_version_id": instance["pending_strategy_version_ids"][0],
        "decision": "approved",
    }
    missing = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        body,
    )
    assert missing.status_code == 428

    first = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        body,
        if_match=instance["revision"],
    )
    assert first.status_code == 201
    stale = professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        {
            "strategy_version_id": instance["pending_strategy_version_ids"][1],
            "decision": "approved",
        },
        if_match=instance["revision"],
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "revision_conflict"


def test_a_caregiver_cannot_review(caregiver) -> None:
    episode_with_recommendations(caregiver)
    inbox = caregiver.get("/api/v1/recommendation-instances")
    assert inbox.status_code == 403
    assert inbox.json()["error"]["code"] == "role_not_allowed"


def test_review_execution_and_outcome_are_separate_rows(caregiver, professional, clock, db) -> None:
    """SPEC 10.4: preferencia, exposición y resultado no se mezclan."""
    episode_id = episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    instance_id = instance["recommendation_instance_id"]
    strategy_version_id = instance["pending_strategy_version_ids"][0]
    professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/reviews",
        {"strategy_version_id": strategy_version_id, "decision": "approved"},
        if_match=instance["revision"],
    )
    clock.advance(hours=1)
    revision = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()[
        "revision"
    ]
    applied_at = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}").json()["as_of_at"]
    execution = caregiver.post(
        f"/api/v1/recommendation-instances/{instance_id}/executions",
        {
            "strategy_version_id": strategy_version_id,
            "status": "applied",
            "applied_at": applied_at,
        },
        if_match=revision,
    )
    assert execution.status_code == 201, execution.text
    caregiver.post(
        f"/api/v1/prediction-episodes/{episode_id}/outcome-reports", {"value": "unknown"}
    )
    counts = {
        table: db.connection.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in ("recommendation_reviews", "strategy_executions", "outcome_reports")
    }
    assert counts == {
        "recommendation_reviews": 1,
        "strategy_executions": 1,
        "outcome_reports": 1,
    }


def test_execution_before_approval_is_rejected(caregiver, professional) -> None:
    """SPEC 10.3: la exposición exige la decisión activa, no solo timestamps."""
    episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    response = caregiver.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/executions",
        {
            "strategy_version_id": instance["pending_strategy_version_ids"][0],
            "status": "not_applied",
        },
        if_match=instance["revision"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "revision_conflict"


def test_suspended_dependency_makes_the_instance_non_actionable(
    caregiver, professional, db
) -> None:
    """INV-28: una fuente retirada suspende dependencias; la historia queda visible."""
    episode_id = episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    instance_id = instance["recommendation_instance_id"]
    strategy_version_id = instance["pending_strategy_version_ids"][0]
    professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/reviews",
        {"strategy_version_id": strategy_version_id, "decision": "approved"},
        if_match=instance["revision"],
    )
    with db.write() as connection:
        connection.execute(
            "UPDATE strategy_versions SET status = 'suspended',"
            " suspended_at = '2026-08-26T00:00:00.000Z' WHERE strategy_version_id = ?",
            (strategy_version_id,),
        )
    professional_view = professional.get(
        f"/api/v1/prediction-episodes/{episode_id}/recommendations"
    ).json()
    suspended = next(
        item
        for item in professional_view["items"]
        if item["strategy_version_id"] == strategy_version_id
    )
    assert suspended["non_actionable"] == "dependency_suspended"

    caregiver_view = caregiver.get(
        f"/api/v1/prediction-episodes/{episode_id}/recommendations"
    ).json()
    assert all(
        item["strategy_version_id"] != strategy_version_id for item in caregiver_view["items"]
    )

    revision = professional_view["revision"]
    blocked = professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/executions",
        {"strategy_version_id": strategy_version_id, "status": "not_applied"},
        if_match=revision,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "recommendation_dependency_suspended"


def test_feedback_never_mutates_the_active_catalog(caregiver, professional, db) -> None:
    """INV-27: el flujo API tampoco muta catálogo, sets ni estrategias."""

    def snapshot() -> list[tuple]:
        return [
            tuple(row)
            for table in (
                "catalog_versions",
                "recommendation_set_versions",
                "strategy_versions",
                "strategy_citations",
                "corpus_versions",
            )
            for row in db.connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        ]

    episode_id = episode_with_recommendations(caregiver)
    before = snapshot()
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = inbox["items"][0]
    professional.post(
        f"/api/v1/recommendation-instances/{instance['recommendation_instance_id']}/reviews",
        {
            "strategy_version_id": instance["pending_strategy_version_ids"][0],
            "decision": "rejected",
        },
        if_match=instance["revision"],
    )
    caregiver.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations")
    assert snapshot() == before


def test_inbox_only_lists_subjects_with_an_active_grant(caregiver, professional, db) -> None:
    episode_with_recommendations(caregiver)
    assert professional.get("/api/v1/recommendation-instances").json()["items"]
    with db.write() as connection:
        connection.execute(
            "UPDATE subject_access_grants SET status = 'revoked',"
            " revoked_at = '2026-01-05T00:00:00.000Z' WHERE actor_id = ?",
            (ids.PROFESSIONAL_A,),
        )
    assert professional.get("/api/v1/recommendation-instances").json()["items"] == []


def test_professional_sees_the_scenario_without_identifiers(caregiver, professional) -> None:
    episode_with_recommendations(caregiver)
    inbox = professional.get("/api/v1/recommendation-instances").json()
    scenario = inbox["items"][0]["scenario"]
    assert scenario is not None
    assert scenario["schema_version"] == "scenario-1"
    assert scenario["field_values"] == {"sleep_quality": "interrupted"}
    serialized = str(scenario)
    for forbidden_value in (ids.SUBJECT_ANA, ids.CAREGIVER_A, "Niña demo 1"):
        assert forbidden_value not in serialized
    assert open_session  # el módulo comparte helpers con el flujo de cuidador
