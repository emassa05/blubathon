"""Live grounded recommendations, feedback and history."""

from __future__ import annotations

from tests.p2.conftest import UngroundedDraftTransport, submit_form
from tools.seed import ids


def test_grounded_draft_becomes_a_matched_recommendation(client, db) -> None:
    submitted = submit_form(client).json()
    response = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matched"
    assert body["citations"]
    assert body["citations"][0]["quote_es"]
    stored = db.connection.execute(
        "SELECT status FROM recommendation_instances WHERE recommendation_instance_id = ?",
        (submitted["recommendation_instance_id"],),
    ).fetchone()
    assert stored["status"] == "matched"


def test_ungrounded_draft_is_never_persisted_as_matched(client, app, db) -> None:
    app.state.registry.core.draft_transport = UngroundedDraftTransport()
    submitted = submit_form(client).json()
    row = db.connection.execute(
        "SELECT status, abstention_reason, action_text_es FROM recommendation_instances"
        " WHERE recommendation_instance_id = ?",
        (submitted["recommendation_instance_id"],),
    ).fetchone()
    assert row["status"] == "abstained"
    assert row["abstention_reason"] == "draft_not_grounded"
    assert row["action_text_es"] is None


def test_bad_feedback_redrafts_without_the_previous_chunk(client) -> None:
    submitted = submit_form(client).json()
    recommendation_id = submitted["recommendation_instance_id"]
    before = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    response = client.post(
        f"/v1/recommendations/{recommendation_id}/feedback",
        json={"rating": "bad", "note_es": None},
    )
    assert response.status_code == 201
    assert response.json()["attempt"] == 1
    after = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    assert after["attempt"] == 2
    assert after["citations"] != before["citations"]


def test_recommendation_list_today_and_history_use_the_new_shape(client) -> None:
    submitted = submit_form(client).json()
    listed = client.get(f"/v1/recommendations?status=matched&child_id={ids.SUBJECT_ANA}&limit=10")
    assert listed.status_code == 200
    assert (
        listed.json()["items"][0]["recommendation_instance_id"]
        == submitted["recommendation_instance_id"]
    )
    today = client.get(f"/v1/children/{ids.SUBJECT_ANA}/recommendations/today")
    assert today.status_code == 200
    assert today.json()["status"] == "matched"
    history = client.get(f"/v1/children/{ids.SUBJECT_ANA}/history")
    assert history.status_code == 200
    assert history.json()["days"][0]["submission_id"] == submitted["submission_id"]


def test_today_without_a_submission_has_an_explicit_state(client) -> None:
    response = client.get(f"/v1/children/{ids.SUBJECT_BETO}/recommendations/today")
    assert response.status_code == 200
    assert response.json()["status"] == "no_submission_today"


def test_websocket_emits_feedback_event(client) -> None:
    submitted = submit_form(client).json()
    with client.websocket_connect("/v1/ws") as websocket:
        response = client.post(
            f"/v1/recommendations/{submitted['recommendation_instance_id']}/feedback",
            json={"rating": "good", "note_es": None},
        )
        assert response.status_code == 201
        event = websocket.receive_json()
    assert event["type"] == "feedback.recorded"
    assert event["rating"] == "good"
    assert "tenant_id" not in event
