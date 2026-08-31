"""Live grounded recommendations, feedback and history."""

from __future__ import annotations

from uuid import UUID

from packages.shared.constants import REVIEW_SAMPLE_DENOMINATOR
from packages.shared.domain.review import REVIEW_SAMPLE_POLICY_VERSION, is_in_review_sample
from tests.p2.conftest import (
    UngroundedDraftTransport,
    UnreachableDraftTransport,
    submit_form,
)
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


def test_a_model_that_cannot_be_reached_abstains_instead_of_staying_pending(
    client, app, db
) -> None:
    """Un modelo caído deja una abstención con motivo, no una fila clavada.

    La generación corre en una tarea de fondo, después de responderle al
    navegador. Una excepción que se escape de ahí no se ve en ninguna pantalla:
    la fila se queda en `pending`, que la interfaz muestra como "estamos
    preparando la recomendación", y no queda nadie preparándola.
    """

    app.state.registry.core.draft_transport = UnreachableDraftTransport()
    submitted = submit_form(client).json()
    row = db.connection.execute(
        "SELECT status, abstention_reason, action_text_es FROM recommendation_instances"
        " WHERE recommendation_instance_id = ?",
        (submitted["recommendation_instance_id"],),
    ).fetchone()
    assert row["status"] == "abstained"
    assert row["abstention_reason"] == "draft_unavailable"
    assert row["action_text_es"] is None
    # Y el cuidador lee el motivo, en vez de una espera que no termina nunca.
    today = client.get(f"/v1/children/{ids.SUBJECT_ANA}/recommendations/today").json()
    assert today["status"] == "abstained"
    assert today["abstention_reason"] == "draft_unavailable"


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


def test_a_professional_can_approve_a_drafted_recommendation(client, db) -> None:
    submitted = submit_form(client).json()
    recommendation_id = submitted["recommendation_instance_id"]
    response = client.post(
        f"/v1/recommendations/{recommendation_id}/review",
        json={"decision": "approved", "note_es": "Encaja con el plan de la sesión."},
    )
    assert response.status_code == 201
    assert response.json()["decision"] == "approved"
    stored = db.connection.execute(
        "SELECT decision, reviewer_role FROM recommendation_decisions"
        " WHERE recommendation_instance_id = ?",
        (recommendation_id,),
    ).fetchone()
    assert stored["decision"] == "approved"
    assert stored["reviewer_role"] == "professional"


def test_the_review_travels_in_the_recommendation_view(client) -> None:
    submitted = submit_form(client).json()
    recommendation_id = submitted["recommendation_instance_id"]
    client.post(f"/v1/recommendations/{recommendation_id}/review", json={"decision": "rejected"})
    view = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    assert view["review_decision"] == "rejected"
    assert view["reviewed_at"] is not None


def test_changing_the_mind_adds_a_row_and_the_last_one_wins(client, db) -> None:
    """Append-only: la revisión anterior sigue siendo auditable."""

    submitted = submit_form(client).json()
    recommendation_id = submitted["recommendation_instance_id"]
    for decision in ("rejected", "approved"):
        assert (
            client.post(
                f"/v1/recommendations/{recommendation_id}/review", json={"decision": decision}
            ).status_code
            == 201
        )
    rows = db.connection.execute(
        "SELECT decision FROM recommendation_decisions WHERE recommendation_instance_id = ?",
        (recommendation_id,),
    ).fetchall()
    assert len(rows) == 2
    view = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    assert view["review_decision"] == "approved"


def test_an_abstained_recommendation_has_no_draft_to_approve(client, app) -> None:
    app.state.registry.core.draft_transport = UngroundedDraftTransport()
    submitted = submit_form(client).json()
    response = client.post(
        f"/v1/recommendations/{submitted['recommendation_instance_id']}/review",
        json={"decision": "approved"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "recommendation_not_reviewable"


def test_a_review_never_redrafts(client) -> None:
    """Un rechazo profesional no vuelve a tirar el dado, a diferencia de un
    `bad` del cuidador."""

    submitted = submit_form(client).json()
    recommendation_id = submitted["recommendation_instance_id"]
    before = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    client.post(f"/v1/recommendations/{recommendation_id}/review", json={"decision": "rejected"})
    after = client.get(
        f"/v1/prediction-episodes/{submitted['prediction_episode_id']}/recommendations"
    ).json()
    assert after["attempt"] == before["attempt"]
    assert after["citations"] == before["citations"]


def test_the_queue_declares_that_it_is_a_sample(client) -> None:
    """Una cola que no dice que es una muestra se lee como el trabajo entero."""

    submit_form(client)
    response = client.get("/v1/recommendations/review-queue")
    assert response.status_code == 200
    body = response.json()
    assert body["sample_denominator"] == REVIEW_SAMPLE_DENOMINATOR
    assert body["sample_policy_version"] == REVIEW_SAMPLE_POLICY_VERSION
    assert body["candidates"] >= len(body["items"])


def test_the_queue_only_carries_the_sampled_recommendations(client) -> None:
    submit_form(client)
    body = client.get("/v1/recommendations/review-queue").json()
    for item in body["items"]:
        assert item["status"] == "matched"
        assert item["in_review_sample"] is True
        assert is_in_review_sample(UUID(item["recommendation_instance_id"]))


def test_the_queue_is_the_same_on_two_consecutive_reads(client) -> None:
    submit_form(client)
    first = client.get("/v1/recommendations/review-queue").json()
    second = client.get("/v1/recommendations/review-queue").json()
    assert [item["recommendation_instance_id"] for item in first["items"]] == [
        item["recommendation_instance_id"] for item in second["items"]
    ]


def test_websocket_emits_the_review_event(client) -> None:
    submitted = submit_form(client).json()
    with client.websocket_connect("/v1/ws") as websocket:
        response = client.post(
            f"/v1/recommendations/{submitted['recommendation_instance_id']}/review",
            json={"decision": "approved"},
        )
        assert response.status_code == 201
        event = websocket.receive_json()
    assert event["type"] == "review.recorded"
    assert event["decision"] == "approved"
    assert "tenant_id" not in event
