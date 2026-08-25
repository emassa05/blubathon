"""Idempotencia y concurrencia (SPEC 11.2; INV-12)."""

from __future__ import annotations

from tests.p2.test_form_sessions import open_session
from tools.seed import ids


def test_same_key_and_payload_returns_the_same_resource(caregiver) -> None:
    payload = {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"}
    first = caregiver.post("/api/v1/form-sessions", payload, key="shared-key")
    second = caregiver.post("/api/v1/form-sessions", payload, key="shared-key")
    assert first.status_code == second.status_code == 201
    assert first.json()["form_session_id"] == second.json()["form_session_id"]


def test_same_key_with_a_different_payload_is_409(caregiver) -> None:
    caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
        key="shared-key",
    )
    response = caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_BETO, "source": "home", "session_kind": "caregiver_daily"},
        key="shared-key",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_conflict"


def test_one_key_on_two_concrete_paths_creates_two_resources(caregiver) -> None:
    """CONVENTIONS 16: la misma key sobre dos IDs concretos exige recursos distintos."""
    first = open_session(caregiver, ids.SUBJECT_ANA)
    second = open_session(caregiver, ids.SUBJECT_BETO)
    body = {"field_code": "sleep_quality", "interaction": "manual", "value": "restorative"}
    one = caregiver.post(
        f"/api/v1/form-sessions/{first['form_session_id']}/answers", body, key="same-key"
    )
    two = caregiver.post(
        f"/api/v1/form-sessions/{second['form_session_id']}/answers", body, key="same-key"
    )
    assert one.status_code == two.status_code == 201
    assert one.json()["field_observation_id"] != two.json()["field_observation_id"]


def test_replay_reauthorizes_and_does_not_reveal_the_stored_response(caregiver, db) -> None:
    """SPEC 11.2: si el grant ya no vale, un replay responde 403."""
    payload = {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"}
    first = caregiver.post("/api/v1/form-sessions", payload, key="replay-key")
    assert first.status_code == 201
    with db.write() as connection:
        connection.execute(
            "UPDATE subject_access_grants SET revoked_at = '2026-01-05T00:00:00.000Z',"
            " status = 'revoked' WHERE actor_id = ? AND subject_id = ?",
            (ids.CAREGIVER_A, ids.SUBJECT_ANA),
        )
    replay = caregiver.post("/api/v1/form-sessions", payload, key="replay-key")
    assert replay.status_code == 403
    assert "form_session_id" not in replay.text


def test_idempotency_scope_is_per_actor(caregiver, professional) -> None:
    payload = {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"}
    one = caregiver.post("/api/v1/form-sessions", payload, key="actor-key")
    two = professional.post("/api/v1/form-sessions", payload, key="actor-key")
    assert one.json()["form_session_id"] != two.json()["form_session_id"]


def test_a_failed_command_rolls_back_completely(caregiver, db) -> None:
    """CONVENTIONS 13: un lote fallido hace rollback; no queda media escritura."""
    session = open_session(caregiver)
    before = db.connection.execute("SELECT COUNT(*) AS n FROM field_observations").fetchone()["n"]
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"field_code": "sleep_hours", "interaction": "manual", "value": 99.0},
    )
    assert response.status_code == 422
    after = db.connection.execute("SELECT COUNT(*) AS n FROM field_observations").fetchone()["n"]
    assert after == before
    keys = db.connection.execute(
        "SELECT COUNT(*) AS n FROM idempotency_keys WHERE normalized_concrete_path LIKE ?",
        (f"%{session['form_session_id']}%",),
    ).fetchone()["n"]
    assert keys == 0
