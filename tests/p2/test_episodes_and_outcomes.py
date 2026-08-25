"""Oportunidad canónica, ventana de 24/48 horas y cadena reporte -> resolución.

Cubre INV-11, INV-13, INV-14, INV-15 y INV-16 desde la API.
"""

from __future__ import annotations

from datetime import timedelta

from apps.api.canonical import canonical_timestamp, parse_timestamp
from tests.p2.test_form_sessions import open_session
from tools.seed import ids


def submit(caller, session_id: str):
    response = caller.post(f"/api/v1/form-sessions/{session_id}/submit")
    assert response.status_code == 201, response.text
    return response.json()


def complete_session(caller, subject_id: str = ids.SUBJECT_ANA):
    session = open_session(caller, subject_id)
    caller.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "sleep_quality",
                "interaction": "manual",
                "value": "interrupted",
            }
        },
    )
    return submit(caller, session["form_session_id"])


def test_submit_creates_a_24_hour_window_and_a_48_hour_deadline(caregiver) -> None:
    result = complete_session(caregiver)
    assert result["status"] == "episode_created"
    episode = caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    start = parse_timestamp(episode["target_start_at"])
    assert episode["as_of_at"] == episode["prediction_at"] == episode["target_start_at"]
    assert parse_timestamp(episode["target_end_at"]) - start == timedelta(hours=24)
    assert parse_timestamp(episode["capture_deadline_at"]) - start == timedelta(hours=48)


def test_second_session_inside_the_window_links_without_a_new_episode(caregiver, db) -> None:
    """INV-13: con target no hay episodios primarios solapados."""
    first = complete_session(caregiver)
    second = complete_session(caregiver)
    assert second["status"] == "episode_linked"
    assert second["linked_prediction_episode_id"] == first["prediction_episode_id"]
    total = db.connection.execute(
        "SELECT COUNT(*) AS total FROM prediction_episodes WHERE subject_id = ?"
        " AND role = 'primary'",
        (ids.SUBJECT_ANA,),
    ).fetchone()
    assert total["total"] == 1
    requests = db.connection.execute(
        "SELECT COUNT(*) AS total FROM outcome_requests WHERE subject_id = ?",
        (ids.SUBJECT_ANA,),
    ).fetchone()
    assert requests["total"] == 1


def test_a_new_opportunity_starts_at_the_previous_target_end(caregiver, clock) -> None:
    first = complete_session(caregiver)
    clock.advance(hours=24)
    second = complete_session(caregiver)
    assert second["status"] == "episode_created"
    assert second["prediction_episode_id"] != first["prediction_episode_id"]


def test_without_a_selectable_target_the_session_closes_without_an_episode(caregiver, db) -> None:
    """INV-13: sin target activo no nace episodio ni outcome request."""
    with db.write() as connection:
        connection.execute(
            "UPDATE target_definition_versions SET approval_status = 'retired',"
            " retired_at = '2026-01-02T00:00:00.000Z'"
        )
    session = open_session(caregiver)
    result = submit(caregiver, session["form_session_id"])
    assert result["status"] == "target_definition_unavailable"
    assert result["prediction_episode_id"] is None
    assert result["reasons"] == ["target_definition_unavailable"]
    row = db.connection.execute(
        "SELECT status, prediction_status FROM form_sessions WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()
    assert row["status"] == "submitted"
    assert row["prediction_status"] == "target_definition_unavailable"
    assert db.connection.execute("SELECT COUNT(*) AS n FROM outcome_requests").fetchone()["n"] == 0


def test_two_effective_target_versions_fail_closed(caregiver, db) -> None:
    """SPEC 4.3: más de una definición activa devuelve `target_definition_ambiguous`."""
    with db.write() as connection:
        row = connection.execute("SELECT * FROM target_definition_versions LIMIT 1").fetchone()
        columns = row.keys()
        values = {key: row[key] for key in columns}
        values["target_definition_version"] = "target-demo-fixture-0.3.1"
        values["effective_from"] = "2026-02-01T00:00:00.000Z"
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(
            f"INSERT INTO target_definition_versions({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values[key] for key in columns),
        )
    session = open_session(caregiver)
    result = submit(caregiver, session["form_session_id"])
    assert result["status"] == "target_definition_unavailable"
    assert result["reasons"] == ["target_definition_ambiguous"]
    row = db.connection.execute(
        "SELECT prediction_status FROM form_sessions WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()
    assert row["prediction_status"] == "target_definition_ambiguous"


def test_snapshot_only_holds_the_projected_observation_ids(caregiver, db) -> None:
    """INV-11: el snapshot persiste los IDs proyectados y no se recalcula."""
    result = complete_session(caregiver)
    snapshot = db.connection.execute(
        "SELECT * FROM feature_snapshots WHERE prediction_episode_id = ?",
        (result["prediction_episode_id"],),
    ).fetchone()
    assert parse_timestamp(snapshot["as_of_at"]) == parse_timestamp(result["submitted_at"])
    assert snapshot["content_sha256"]
    assert snapshot["input_data_origin"] == "synthetic"


# -- outcomes ------------------------------------------------------------


def report(caller, episode_id: str, payload: dict):
    return caller.post(f"/api/v1/prediction-episodes/{episode_id}/outcome-reports", payload)


def test_explicit_unknown_leaves_the_resolution_pending(caregiver) -> None:
    """INV-14: un `unknown` explícito no resuelve nada."""
    result = complete_session(caregiver)
    response = report(caregiver, result["prediction_episode_id"], {"value": "unknown"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["report"]["value"] == "unknown"
    assert body["report"]["timing_status"] == "early"
    assert body["resolution"]["status"] == "pending"
    assert body["request_state"] == "open"


def test_early_no_stays_provisional(caregiver) -> None:
    """INV-14: un `no` temprano se conserva pero no cierra la ventana."""
    result = complete_session(caregiver)
    body = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert body["report"]["timing_status"] == "early"
    assert body["resolution"]["status"] == "pending"


def test_valid_early_yes_resolves_the_window(caregiver, clock) -> None:
    """INV-13: un `yes` temprano válido resuelve antes del cierre."""
    result = complete_session(caregiver)
    clock.advance(hours=3)
    occurred_at = canonical_timestamp(parse_timestamp(result["submitted_at"]) + timedelta(hours=2))
    body = report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": occurred_at},
    ).json()
    assert body["resolution"]["status"] == "yes"
    assert body["resolution"]["qualifying_report_id"] == body["report"]["outcome_report_id"]
    assert body["request_state"] == "reported"


def test_yes_outside_the_window_is_rejected(caregiver, clock) -> None:
    result = complete_session(caregiver)
    clock.advance(hours=30)
    outside = canonical_timestamp(parse_timestamp(result["submitted_at"]) + timedelta(hours=26))
    response = report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": outside},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "outcome_report_invalid_timing"


def test_yes_at_the_exact_window_start_is_rejected(caregiver, clock) -> None:
    """La ventana es `(target_start_at, target_end_at]`: el inicio queda abierto."""
    result = complete_session(caregiver)
    clock.advance(hours=1)
    response = report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": result["submitted_at"]},
    )
    assert response.status_code == 422


def test_incompatible_reports_produce_conflicted(caregiver, clock) -> None:
    """INV-15: reportes incompatibles producen `conflicted` de forma permanente."""
    result = complete_session(caregiver)
    occurred_at = canonical_timestamp(parse_timestamp(result["submitted_at"]) + timedelta(hours=2))
    clock.advance(hours=25)  # ahora los reportes son `on_time`
    report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": occurred_at},
    )
    body = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert body["resolution"]["status"] == "conflicted"
    assert body["resolution"]["ever_conflicted"] is True
    assert body["request_state"] == "conflicted"


def test_ever_conflicted_never_returns_to_false(caregiver, clock, db) -> None:
    result = complete_session(caregiver)
    occurred_at = canonical_timestamp(parse_timestamp(result["submitted_at"]) + timedelta(hours=2))
    clock.advance(hours=25)
    yes = report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": occurred_at},
    ).json()
    no = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert no["resolution"]["ever_conflicted"] is True
    # Una corrección deja un solo reporte elegible, pero la historia se conserva.
    corrected = caregiver.post(
        f"/api/v1/prediction-episodes/{result['prediction_episode_id']}/outcome-reports",
        {
            "value": "yes",
            "occurred_at": occurred_at,
            "supersedes_id": no["report"]["outcome_report_id"],
        },
    ).json()
    assert corrected["resolution"]["status"] == "yes"
    assert corrected["resolution"]["ever_conflicted"] is True
    versions = db.connection.execute(
        "SELECT ever_conflicted FROM outcome_resolutions WHERE prediction_episode_id = ?"
        " ORDER BY resolution_version",
        (result["prediction_episode_id"],),
    ).fetchall()
    flags = [bool(row["ever_conflicted"]) for row in versions]
    # Monotónico: nunca vuelve a false una vez marcado.
    assert flags == sorted(flags)
    assert flags[-1] is True
    assert True in flags
    assert yes["resolution"]["status"] == "yes"


def test_deadline_without_a_conclusive_report_becomes_unknown_and_missing(caregiver, clock) -> None:
    """INV-14: al deadline pasa a `unknown`, nunca a `no`."""
    result = complete_session(caregiver)
    report(caregiver, result["prediction_episode_id"], {"value": "unknown"})
    clock.advance(hours=49)
    episode = caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    assert episode["resolution_status"] == "unknown"
    assert episode["outcome_state"] == "missing"


def test_a_late_report_is_stored_but_does_not_resolve(caregiver, clock, db) -> None:
    """INV-16: un outcome `late` queda fuera del dataset primario."""
    result = complete_session(caregiver)
    clock.advance(hours=49)
    body = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert body["report"]["timing_status"] == "late"
    assert body["resolution"]["status"] == "unknown"
    stored = db.connection.execute(
        "SELECT timing_status FROM outcome_reports WHERE outcome_report_id = ?",
        (body["report"]["outcome_report_id"],),
    ).fetchone()
    assert stored["timing_status"] == "late"


def test_outcome_inbox_lists_only_pending_requests_with_an_open_deadline(caregiver, clock) -> None:
    result = complete_session(caregiver)
    inbox = caregiver.get("/api/v1/outcome-requests").json()
    assert [item["prediction_episode_id"] for item in inbox["items"]] == [
        result["prediction_episode_id"]
    ]
    assert inbox["items"][0]["state"] == "open"
    clock.advance(hours=49)
    assert caregiver.get("/api/v1/outcome-requests").json()["items"] == []


def test_no_occurred_at_for_a_negative_report(caregiver) -> None:
    result = complete_session(caregiver)
    response = report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "no", "occurred_at": result["submitted_at"]},
    )
    assert response.status_code == 422
    # `OutcomeReportRequest` de P1 rechaza la combinación en el contrato, así
    # que la solicitud no llega al servicio y el código es el de validación.
    assert response.json()["error"]["code"] == "validation_error"
