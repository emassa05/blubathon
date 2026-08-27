"""End-to-end v0.4 caregiver journey."""

from __future__ import annotations

from tests.p2.conftest import submit_form
from tools.seed import ids


def test_submit_read_feedback_and_report_outcome(client, clock) -> None:
    children = client.get("/v1/children")
    assert children.status_code == 200

    plan = client.post(
        f"/v1/children/{ids.SUBJECT_ANA}/form-plan",
        json={"source": "caregiver_daily", "answers": {}},
    )
    assert plan.status_code == 200

    submitted = submit_form(client).json()
    recommendation = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    assert recommendation["status"] == "matched"

    feedback = client.post(
        f"/v1/recommendations/{submitted['recommendation_instance_id']}/feedback",
        json={"rating": "good", "note_es": None},
    )
    assert feedback.status_code == 201

    clock.advance(hours=25)
    outcome = client.post(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/outcome-reports",
        json={"value": "no"},
    )
    assert outcome.status_code == 201
    assert outcome.json()["resolution"]["status"] == "no"

    history = client.get(f"/v1/children/{ids.SUBJECT_ANA}/history").json()
    assert history["days"][0]["recommendation"]["rating"] == "good"
    assert history["days"][0]["outcome"]["status"] == "no"
