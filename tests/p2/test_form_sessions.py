"""Sesión de formulario: auditoría, sugerencias, entry mode y accesibilidad del plan.

Cubre INV-01, INV-05, INV-07 y INV-10 desde la API.
"""

from __future__ import annotations

from apps.api.contracts.enums import Source
from apps.api.contracts.field_catalog import applicable_fields
from tools.seed import ids


def open_session(caller, subject_id: str = ids.SUBJECT_ANA, source: str = "home"):
    response = caller.post(
        "/api/v1/form-sessions",
        {"subject_id": subject_id, "source": source, "session_kind": "caregiver_daily"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_open_session_requires_idempotency_key(caregiver) -> None:
    response = caregiver.post_raw(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"


def test_plan_keeps_every_applicable_field(caregiver) -> None:
    """INV-10: `highlighted + tail` conserva todos los campos aplicables."""
    session = open_session(caregiver)
    planned = {item["field_code"] for item in session["highlighted"] + session["tail"]}
    assert planned == set(applicable_fields(Source.HOME))


def test_audit_mode_is_stable_across_reloads(caregiver) -> None:
    """INV-05: reabrir una sesión no cambia `audit_mode`."""
    session = open_session(caregiver)
    for _ in range(3):
        reloaded = caregiver.get(f"/api/v1/form-sessions/{session['form_session_id']}").json()
        assert reloaded["audit_mode"] == session["audit_mode"]
        assert reloaded["form_policy_version"] == session["form_policy_version"]


def test_untouched_suggestion_creates_no_observation(caregiver, db) -> None:
    """INV-01: un default no tocado produce cero observaciones."""
    session = open_session(caregiver)
    suggested = [
        item for item in session["highlighted"] + session["tail"] if item["default"] is not None
    ]
    assert suggested, "el fixture debe ofrecer al menos una sugerencia"
    rows = db.connection.execute(
        "SELECT COUNT(*) AS total FROM field_observations WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()
    assert rows["total"] == 0


def test_suggestion_at_exactly_the_threshold_is_not_shown(caregiver) -> None:
    """INV-07: `lower = 0.70` no muestra sugerencia; el corte es estricto."""
    session = open_session(caregiver)
    by_code = {item["field_code"]: item for item in session["highlighted"] + session["tail"]}
    # El fixture del adaptador declara activity_participation con lower_bound=0.70.
    assert by_code["activity_participation"]["default"] is None
    assert by_code["food_changes"]["default"] is not None


def test_voi_is_null_not_zero(caregiver) -> None:
    """INV-09 desde la API: sin modelo, VoI es `null`."""
    session = open_session(caregiver)
    assert session["voi_status"] == "unavailable_model"
    assert all(item["voi_nats"] is None for item in session["highlighted"] + session["tail"])


def test_manual_answer_over_a_presented_default_is_default_edited(caregiver) -> None:
    """SPEC 5.5 regla 7: el cliente no puede declararlo `manual_no_default`."""
    session = open_session(caregiver)
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"answer": {"field_code": "food_changes", "interaction": "manual", "value": True}},
    )
    assert response.status_code == 201, response.text
    assert response.json()["entry_mode"] == "default_edited"


def test_accepting_a_default_stores_the_presented_value(caregiver, db) -> None:
    session = open_session(caregiver)
    presented = next(
        item
        for item in session["highlighted"] + session["tail"]
        if item["field_code"] == "food_changes"
    )
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "food_changes",
                "interaction": "accept_default",
                # `AnswerSubmission` exige declarar el valor aceptado; el
                # servidor lo compara con el presentado antes de guardarlo.
                "value": presented["default"]["value"],
                "default_presentation_id": presented["default"]["presentation_id"],
            }
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["entry_mode"] == "default_accepted"
    row = db.connection.execute(
        "SELECT value, entry_mode FROM field_observations WHERE form_session_id = ?"
        " AND field_code = 'food_changes'",
        (session["form_session_id"],),
    ).fetchone()
    assert row["value"] == "false"
    assert row["entry_mode"] == "default_accepted"


def test_explicit_unknown_persists_without_a_value(caregiver, db) -> None:
    """SPEC 8.2: `unknown` es una decisión explícita sin valor."""
    session = open_session(caregiver)
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"answer": {"field_code": "sleep_quality", "interaction": "unknown"}},
    )
    assert response.status_code == 201
    assert response.json()["entry_mode"] == "explicit_unknown"
    row = db.connection.execute(
        "SELECT value, entry_mode FROM field_observations WHERE form_session_id = ?"
        " AND field_code = 'sleep_quality'",
        (session["form_session_id"],),
    ).fetchone()
    assert row["value"] is None
    assert row["entry_mode"] == "explicit_unknown"


def test_field_not_allowed_for_source_is_rejected(caregiver) -> None:
    """SPEC 5.4: `attendance_status` no se registra desde `home`."""
    session = open_session(caregiver)
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "attendance_status",
                "interaction": "manual",
                "value": "present",
            }
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "field_not_allowed_for_source"


def test_out_of_range_value_is_rejected_not_coerced(caregiver) -> None:
    session = open_session(caregiver)
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"answer": {"field_code": "sleep_hours", "interaction": "manual", "value": 25.0}},
    )
    assert response.status_code == 422


def test_unknown_category_fails_closed(caregiver) -> None:
    """INV-35: ningún adaptador convierte una categoría desconocida en `null`."""
    session = open_session(caregiver)
    response = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"answer": {"field_code": "sleep_quality", "interaction": "manual", "value": "muy_mal"}},
    )
    assert response.status_code == 422


def test_correction_keeps_the_original_row(caregiver, db) -> None:
    """CONVENTIONS 8.1: una corrección usa `supersedes_id` y no sobrescribe."""
    session = open_session(caregiver)
    first = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"answer": {"field_code": "night_awakenings", "interaction": "manual", "value": 2}},
    ).json()
    second = caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "night_awakenings",
                "interaction": "manual",
                "value": 3,
                "supersedes_id": first["field_observation_id"],
            }
        },
    )
    assert second.status_code == 201
    rows = db.connection.execute(
        "SELECT value, supersedes_id FROM field_observations WHERE form_session_id = ?"
        " AND field_code = 'night_awakenings' ORDER BY ingested_at, field_observation_id",
        (session["form_session_id"],),
    ).fetchall()
    # La fila original se conserva; la corrección la enlaza con `supersedes_id`.
    assert {row["value"] for row in rows} == {"2", "3"}
    corrections = [row for row in rows if row["supersedes_id"] is not None]
    assert len(corrections) == 1
    assert corrections[0]["value"] == "3"
    assert corrections[0]["supersedes_id"] == first["field_observation_id"]


def test_a_closed_session_does_not_present_new_questions(caregiver, db) -> None:
    """SPEC 6.10: recalcular tras el cierre reiniciaría el reloj de antigüedad."""
    session = open_session(caregiver)
    caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "sleep_quality",
                "interaction": "manual",
                "value": "restorative",
            }
        },
    )
    caregiver.post(f"/api/v1/form-sessions/{session['form_session_id']}/submit")
    before = db.connection.execute(
        "SELECT field_code FROM question_presentations WHERE form_session_id = ?"
        " ORDER BY field_code",
        (session["form_session_id"],),
    ).fetchall()

    view = caregiver.get(f"/api/v1/form-sessions/{session['form_session_id']}").json()
    after = db.connection.execute(
        "SELECT field_code FROM question_presentations WHERE form_session_id = ?"
        " ORDER BY field_code",
        (session["form_session_id"],),
    ).fetchall()
    assert [row["field_code"] for row in after] == [row["field_code"] for row in before]
    assert view["plan_source"] == "persisted"
    assert view["status"] == "submitted"
    # Todos los campos aplicables siguen visibles (INV-10).
    planned = {item["field_code"] for item in view["highlighted"] + view["tail"]}
    assert planned == set(applicable_fields(Source.HOME))
