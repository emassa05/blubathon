"""Stateless submission, prediction and outcome behavior."""

from __future__ import annotations

from tests.p2.conftest import submit_form
from tools.seed import ids


def test_form_plan_is_stateless_and_does_not_write(client, db) -> None:
    before = db.connection.total_changes
    response = client.post(
        f"/v1/children/{ids.SUBJECT_ANA}/form-plan",
        json={"source": "caregiver_daily", "answers": {}},
    )
    assert response.status_code == 200
    assert response.json()["voi_status"] == "unavailable_model"
    assert db.connection.total_changes == before


def test_unknown_answer_creates_no_observation(client, db) -> None:
    response = submit_form(
        client,
        answers=[{"field_code": "sleep_quality", "value": None, "interaction": "unknown"}],
    )
    assert response.status_code == 201
    submission_id = response.json()["submission_id"]
    count = db.connection.execute(
        "SELECT COUNT(*) AS n FROM field_observations WHERE form_session_id = ?",
        (submission_id,),
    ).fetchone()["n"]
    assert count == 0


def test_submission_creates_episode_outcome_and_recommendation(client) -> None:
    response = submit_form(client)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "episode_created"
    assert body["prediction_episode_id"]
    assert body["recommendation_instance_id"]
    assert body["outcome_request_id"]

    episode = client.get(f"/v1/prediction-episodes/{body['prediction_episode_id']}")
    assert episode.status_code == 200
    # El challenger es operativo, así que sale en la respuesta como cualquier
    # otro track. Sin modelo entrenado no puntúa, y entonces lo que publica es
    # su abstención con el motivo: nunca un número.
    tracks = {item["track_id"]: item for item in episode.json()["outputs"]}
    challenger = tracks.get("real_logit_challenger_v1")
    if challenger is not None and challenger["status"] != "ok":
        assert challenger["probability"] is None
        assert challenger["abstention_reasons"]


def test_second_submission_links_the_open_episode(client) -> None:
    first = submit_form(client).json()
    second = submit_form(client).json()
    assert second == {
        "submission_id": second["submission_id"],
        "status": "episode_linked",
        "prediction_episode_id": first["prediction_episode_id"],
        "recommendation_instance_id": None,
        "outcome_request_id": None,
    }


def test_any_caller_can_report_an_outcome(client, clock) -> None:
    submitted = submit_form(client).json()
    clock.advance(hours=1)
    response = client.post(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/outcome-reports",
        json={"value": "yes", "occurred_at": "2026-08-25T12:30:00.000Z"},
    )
    assert response.status_code == 201
    assert response.json()["resolution"]["status"] == "yes"
