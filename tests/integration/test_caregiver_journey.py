"""Journey completo de cuidador (TAREAS M3, "Test E2E cuidador")."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from apps.api.canonical import format_timestamp, parse_timestamp
from tools.seed import ids

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "caregiver_journey.json").read_text(encoding="utf-8")
)


def test_caregiver_journey_end_to_end(caregiver, other_tenant_caregiver, db, clock) -> None:
    # 1-2. Con el target demo sembrado, se abre la sesión y queda la auditoría.
    opened = caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    )
    assert opened.status_code == 201
    session = opened.json()
    session_id = session["form_session_id"]
    assert "no monitorea emergencias" in session["emergency_notice_es"]

    # 3. Recargar no cambia la auditoría.
    reloaded = caregiver.get(f"/api/v1/form-sessions/{session_id}").json()
    assert reloaded["audit_mode"] == session["audit_mode"]

    # 4-5. Se deja una sugerencia sin tocar y se responde otro campo.
    suggested = [
        item for item in session["highlighted"] + session["tail"] if item["default"] is not None
    ]
    assert suggested
    answer = FIXTURE["answers"][0]
    assert caregiver.post(f"/api/v1/form-sessions/{session_id}/answers", answer).status_code == 201

    # 6. Se envía y nace el episodio primario.
    submitted = caregiver.post(f"/api/v1/form-sessions/{session_id}/submit").json()
    assert submitted["status"] == "episode_created"
    episode_id = submitted["prediction_episode_id"]

    # Solo se persistió el campo tocado.
    rows = db.connection.execute(
        "SELECT field_code FROM field_observations WHERE form_session_id = ?",
        (session_id,),
    ).fetchall()
    assert [row["field_code"] for row in rows] == [answer["field_code"]]

    # 7. El episodio muestra abstención real y score de simulación etiquetado.
    episode = caregiver.get(f"/api/v1/prediction-episodes/{episode_id}").json()
    tracks = {item["track_id"]: item for item in episode["outputs"]}
    assert tracks["real_personal_baseline_v1"]["status"] == "abstained"
    assert tracks["synthetic_reference_v021"]["intended_use"] == "simulation_only"
    assert "real_logit_challenger_v1" not in tracks

    # 8. Un `unknown` explícito deja la resolución pending.
    unknown = caregiver.post(
        f"/api/v1/prediction-episodes/{episode_id}/outcome-reports", {"value": "unknown"}
    ).json()
    assert unknown["resolution"]["status"] == "pending"
    assert unknown["request_status"] == "open"

    # 9. Después se reporta un outcome concluyente.
    clock.advance(hours=5)
    occurred_at = format_timestamp(parse_timestamp(submitted["submitted_at"]) + timedelta(hours=4))
    conclusive = caregiver.post(
        f"/api/v1/prediction-episodes/{episode_id}/outcome-reports",
        {"value": "yes", "occurred_at": occurred_at},
        key="outcome-yes",
    )
    assert conclusive.json()["resolution"]["status"] == "yes"

    # 10. Repetir el POST devuelve el mismo recurso.
    replay = caregiver.post(
        f"/api/v1/prediction-episodes/{episode_id}/outcome-reports",
        {"value": "yes", "occurred_at": occurred_at},
        key="outcome-yes",
    )
    assert replay.status_code == 201
    assert (
        replay.json()["report"]["outcome_report_id"]
        == conclusive.json()["report"]["outcome_report_id"]
    )

    # 11. Otro sujeto del mismo tenant sin grant devuelve 403 auditado.
    denied = caregiver.post(
        "/api/v1/form-sessions",
        {
            "subject_id": ids.SUBJECT_SIN_GRANT,
            "source": "home",
            "session_kind": "caregiver_daily",
        },
    )
    assert denied.status_code == 403
    audited = db.connection.execute(
        "SELECT decision FROM audit_events WHERE subject_id = ? AND decision = 'denied'",
        (ids.SUBJECT_SIN_GRANT,),
    ).fetchall()
    assert audited

    # Un tenant ajeno tampoco alcanza el episodio.
    assert (
        other_tenant_caregiver.get(f"/api/v1/prediction-episodes/{episode_id}").status_code == 404
    )

    # 12. Sin target seleccionable, la sesión cierra sin episodio ni request.
    with db.write() as connection:
        connection.execute(
            "UPDATE target_definition_versions SET approval_status = 'retired',"
            " retired_at = '2026-08-25T00:00:00.000Z'"
        )
    clock.advance(hours=30)
    second = caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    ).json()
    closed = caregiver.post(f"/api/v1/form-sessions/{second['form_session_id']}/submit").json()
    assert closed["status"] == "target_definition_unavailable"
    assert closed["prediction_episode_id"] is None
    episodes = db.connection.execute(
        "SELECT COUNT(*) AS n FROM prediction_episodes WHERE subject_id = ?",
        (ids.SUBJECT_ANA,),
    ).fetchone()
    assert episodes["n"] == 1
