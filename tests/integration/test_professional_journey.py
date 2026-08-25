"""Journey profesional: inbox, revisión, sustitución, ejecución y outcome.

TAREAS M4 P2.7-P2.8. Demuestra que aprobación, aplicación y resultado quedan
separados (SPEC 10.4) y que solo lo aprobado llega al cuidador.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from apps.api.canonical import canonical_timestamp, parse_timestamp
from tools.seed import ids

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "professional_journey.json").read_text(encoding="utf-8")
)


@pytest.fixture
def catalog_profile() -> str:
    return "fixture-active"


def test_professional_journey_end_to_end(caregiver, professional, clock, db) -> None:
    assert FIXTURE["journey"] == "professional_review_demo"

    # 1. La cuidadora cierra una sesión y nace la instancia con el episodio.
    session = caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    ).json()
    caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "sleep_quality",
                "interaction": "manual",
                "value": "interrupted",
            }
        },
    )
    submitted = caregiver.post(f"/api/v1/form-sessions/{session['form_session_id']}/submit").json()
    episode_id = submitted["prediction_episode_id"]
    instance_id = submitted["recommendation_instance_id"]
    assert instance_id is not None

    # 2. Mientras nadie revisa, la familia no ve nada.
    caregiver_view = caregiver.get(
        f"/api/v1/prediction-episodes/{episode_id}/recommendations"
    ).json()
    assert caregiver_view["status"] == "awaiting_professional_review"

    # 3. El inbox profesional muestra el escenario sin identificadores.
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = next(
        item for item in inbox["items"] if item["recommendation_instance_id"] == instance_id
    )
    assert instance["scenario"]["field_values"] == {"sleep_quality": "interrupted"}
    assert ids.SUBJECT_ANA not in json.dumps(instance["scenario"])
    pending = instance["pending_strategy_version_ids"]
    assert len(pending) == 2

    # 4. Se aprueba una estrategia.
    approved = professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/reviews",
        {"strategy_version_id": pending[0], "decision": "approved"},
        if_match=instance["revision"],
    )
    assert approved.status_code == 201

    # 5. Se sustituye la otra por un plan humano.
    revision = professional.get(f"/api/v1/prediction-episodes/{episode_id}/recommendations").json()[
        "revision"
    ]
    substituted = professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/reviews",
        {
            "strategy_version_id": pending[1],
            "decision": "human_plan_substituted",
            "human_plan_action_text_es": "Acordamos un aviso verbal breve antes de cada cambio.",
            "human_plan_allowed_executor_roles": ["caregiver"],
        },
        if_match=revision,
    )
    assert substituted.status_code == 201
    human_plan_version_id = substituted.json()["human_plan_version_id"]

    # 6. La familia ve exactamente lo aprobado y lo sustituido.
    caregiver_view = caregiver.get(
        f"/api/v1/prediction-episodes/{episode_id}/recommendations"
    ).json()
    assert caregiver_view["status"] == "matched"
    kinds = {item["item_type"] for item in caregiver_view["items"]}
    assert kinds == {"strategy", "human_plan"}
    human_item = next(item for item in caregiver_view["items"] if item["item_type"] == "human_plan")
    assert human_item["citations"] == []
    strategy_item = next(
        item for item in caregiver_view["items"] if item["item_type"] == "strategy"
    )
    assert strategy_item["citations"]
    assert strategy_item["citations"][0]["canonical_url"].startswith("https://")

    # 7. La cuidadora registra la aplicación del plan humano.
    clock.advance(hours=2)
    applied_at = canonical_timestamp(
        parse_timestamp(submitted["submitted_at"]) + timedelta(hours=1)
    )
    execution = caregiver.post(
        f"/api/v1/recommendation-instances/{instance_id}/executions",
        {
            "human_plan_version_id": human_plan_version_id,
            "status": "applied",
            "applied_at": applied_at,
        },
        if_match=caregiver_view["revision"],
    )
    assert execution.status_code == 201, execution.text
    assert execution.json()["exposure_eligible"] is True

    # 8. El outcome se reporta aparte.
    occurred_at = canonical_timestamp(
        parse_timestamp(submitted["submitted_at"]) + timedelta(hours=2)
    )
    outcome = caregiver.post(
        f"/api/v1/prediction-episodes/{episode_id}/outcome-reports",
        {"value": "yes", "occurred_at": occurred_at},
    ).json()
    assert outcome["resolution"]["status"] == "yes"

    # 9. Tres entidades separadas, ninguna derivada de la otra.
    reviews = db.connection.execute(
        "SELECT decision FROM recommendation_reviews WHERE recommendation_instance_id = ?"
        " ORDER BY decision",
        (instance_id,),
    ).fetchall()
    executions = db.connection.execute(
        "SELECT status, human_plan_version_id, strategy_version_id FROM strategy_executions"
        " WHERE recommendation_instance_id = ?",
        (instance_id,),
    ).fetchall()
    outcomes = db.connection.execute(
        "SELECT value FROM outcome_reports WHERE prediction_episode_id = ?",
        (episode_id,),
    ).fetchall()
    assert [row["decision"] for row in reviews] == ["approved", "human_plan_substituted"]
    assert len(executions) == 1
    assert executions[0]["strategy_version_id"] is None
    assert executions[0]["human_plan_version_id"] == human_plan_version_id
    assert [row["value"] for row in outcomes] == ["yes"]


def test_a_late_application_is_kept_but_not_attributed(caregiver, professional, clock) -> None:
    """SPEC 10.3: una aplicación fuera de la ventana no se atribuye al outcome."""
    session = caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    ).json()
    caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "sleep_quality",
                "interaction": "manual",
                "value": "interrupted",
            }
        },
    )
    submitted = caregiver.post(f"/api/v1/form-sessions/{session['form_session_id']}/submit").json()
    instance_id = submitted["recommendation_instance_id"]
    inbox = professional.get("/api/v1/recommendation-instances").json()
    instance = next(
        item for item in inbox["items"] if item["recommendation_instance_id"] == instance_id
    )
    strategy_version_id = instance["pending_strategy_version_ids"][0]
    professional.post(
        f"/api/v1/recommendation-instances/{instance_id}/reviews",
        {"strategy_version_id": strategy_version_id, "decision": "approved"},
        if_match=instance["revision"],
    )
    clock.advance(hours=30)
    revision = caregiver.get(
        f"/api/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()["revision"]
    late_applied_at = canonical_timestamp(
        parse_timestamp(submitted["submitted_at"]) + timedelta(hours=26)
    )
    execution = caregiver.post(
        f"/api/v1/recommendation-instances/{instance_id}/executions",
        {
            "strategy_version_id": strategy_version_id,
            "status": "applied",
            "applied_at": late_applied_at,
        },
        if_match=revision,
    )
    assert execution.status_code == 201
    # Se conserva como historia, pero fuera de la ventana no es elegible.
    assert execution.json()["exposure_eligible"] is False
