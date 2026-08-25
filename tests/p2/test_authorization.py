"""Tenant, rol, acreditación, capability y grant (SPEC 13; INV-31).

Cada denegación deja evento de auditoría y ninguna filtra la existencia de un
sujeto ajeno.
"""

from __future__ import annotations

from tests.p2.test_form_sessions import open_session
from tools.seed import ids


def _open(caller, subject_id: str):
    return caller.post(
        "/api/v1/form-sessions",
        {"subject_id": subject_id, "source": "home", "session_kind": "caregiver_daily"},
    )


def test_cross_tenant_access_is_403_and_audited(other_tenant_caregiver, db) -> None:
    response = _open(other_tenant_caregiver, ids.SUBJECT_ANA)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_tenant"
    row = db.connection.execute(
        "SELECT decision, reason_code FROM audit_events WHERE subject_id = ?"
        " ORDER BY occurred_at DESC LIMIT 1",
        (ids.SUBJECT_ANA,),
    ).fetchone()
    assert row["decision"] == "denied"
    assert row["reason_code"] == "cross_tenant"


def test_same_tenant_without_grant_is_403_and_audited(caregiver, db) -> None:
    response = _open(caregiver, ids.SUBJECT_SIN_GRANT)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "subject_access_denied"
    row = db.connection.execute(
        "SELECT decision, reason_code FROM audit_events WHERE subject_id = ?"
        " ORDER BY occurred_at DESC LIMIT 1",
        (ids.SUBJECT_SIN_GRANT,),
    ).fetchone()
    assert row["decision"] == "denied"
    assert row["reason_code"] == "subject_access_denied"


def test_revoked_grant_blocks_further_access(caregiver, db) -> None:
    assert _open(caregiver, ids.SUBJECT_ANA).status_code == 201
    with db.write() as connection:
        connection.execute(
            "UPDATE subject_access_grants SET revoked_at = '2026-01-05T00:00:00.000Z',"
            " status = 'revoked' WHERE actor_id = ? AND subject_id = ?",
            (ids.CAREGIVER_A, ids.SUBJECT_ANA),
        )
    assert _open(caregiver, ids.SUBJECT_ANA).status_code == 403


def test_professional_without_accreditation_is_403(unaccredited_professional) -> None:
    response = _open(unaccredited_professional, ids.SUBJECT_ANA)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "accreditation_required"


def test_lists_are_filtered_in_sql_by_grant(caregiver, db) -> None:
    """SPEC 13.2: no se cargan filas prohibidas para filtrarlas en aplicación."""
    body = caregiver.get("/api/v1/session").json()
    assert ids.SUBJECT_SIN_GRANT not in {item["subject_id"] for item in body["subjects"]}
    with db.write() as connection:
        connection.execute(
            "UPDATE subject_access_grants SET revoked_at = '2026-01-05T00:00:00.000Z',"
            " status = 'revoked' WHERE actor_id = ? AND subject_id = ?",
            (ids.CAREGIVER_A, ids.SUBJECT_BETO),
        )
    body = caregiver.get("/api/v1/session").json()
    assert {item["subject_id"] for item in body["subjects"]} == {ids.SUBJECT_ANA}


def test_reading_another_tenants_session_looks_like_not_found(
    caregiver, other_tenant_caregiver
) -> None:
    session = open_session(caregiver)
    response = other_tenant_caregiver.get(f"/api/v1/form-sessions/{session['form_session_id']}")
    assert response.status_code == 404


def test_audit_events_never_carry_clinical_payload(caregiver, db) -> None:
    """CONVENTIONS 15: la auditoría guarda identificadores y códigos, no valores."""
    session = open_session(caregiver)
    caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {
            "answer": {
                "field_code": "notes",
                "interaction": "manual",
                "value": "texto clínico secreto",
            }
        },
    )
    columns = [
        row[1] for row in db.connection.execute("PRAGMA table_info(audit_events)").fetchall()
    ]
    assert "payload" not in columns and "detail" not in columns
    rows = db.connection.execute("SELECT * FROM audit_events").fetchall()
    for row in rows:
        assert "texto clínico secreto" not in " ".join(str(row[column]) for column in columns)
