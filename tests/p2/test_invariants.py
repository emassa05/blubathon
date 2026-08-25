"""Invariantes de `SPEC 17` asignados a P2 en `TAREAS 11`.

Cada regla tiene un test nombrado (CONVENTIONS 16). Los invariantes algorítmicos
y de contrato viven en `tests/p1`, propiedad de P1.
"""

from __future__ import annotations

from datetime import timedelta

from apps.api.canonical import format_timestamp, parse_timestamp
from apps.api.store.json_columns import load_list
from tests.p2.test_episodes_and_outcomes import complete_session, report
from tests.p2.test_form_sessions import open_session
from tools.seed import ids


def test_inv_01_an_untouched_default_produces_zero_observations(caregiver, db) -> None:
    session = open_session(caregiver)
    assert any(item["default"] is not None for item in session["highlighted"] + session["tail"])
    total = db.connection.execute(
        "SELECT COUNT(*) AS n FROM field_observations WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()["n"]
    assert total == 0


def test_inv_05_reopening_a_session_does_not_change_audit_mode(caregiver, db) -> None:
    session = open_session(caregiver)
    stored = db.connection.execute(
        "SELECT audit_mode, audit_bucket FROM form_sessions WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()
    for _ in range(3):
        reloaded = caregiver.get(f"/api/v1/form-sessions/{session['form_session_id']}").json()
        assert reloaded["audit_mode"] == bool(stored["audit_mode"])
    after = db.connection.execute(
        "SELECT audit_mode, audit_bucket FROM form_sessions WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchone()
    assert after["audit_bucket"] == stored["audit_bucket"]


def test_inv_08_answering_the_filter_with_no_creates_no_queue_observations(caregiver, db) -> None:
    """Responder "No" solo guarda `relevant_event_flag=false` (SPEC 6.9)."""
    session = open_session(caregiver)
    caregiver.post(
        f"/api/v1/form-sessions/{session['form_session_id']}/answers",
        {"field_code": "relevant_event_flag", "interaction": "manual", "value": False},
    )
    rows = db.connection.execute(
        "SELECT field_code, value FROM field_observations WHERE form_session_id = ?",
        (session["form_session_id"],),
    ).fetchall()
    assert [(row["field_code"], row["value"]) for row in rows] == [("relevant_event_flag", "false")]


def test_inv_11_a_later_correction_does_not_alter_a_persisted_snapshot(
    caregiver, clock, db
) -> None:
    """Datos o correcciones posteriores a `as_of_at` no alteran el snapshot."""
    result = complete_session(caregiver)
    snapshot = db.connection.execute(
        "SELECT projected_observation_ids, content_sha256 FROM feature_snapshots"
        " WHERE prediction_episode_id = ?",
        (result["prediction_episode_id"],),
    ).fetchone()
    before_ids = load_list(snapshot["projected_observation_ids"])
    before_hash = snapshot["content_sha256"]

    clock.advance(hours=2)
    later = open_session(caregiver)
    caregiver.post(
        f"/api/v1/form-sessions/{later['form_session_id']}/answers",
        {"field_code": "sleep_quality", "interaction": "manual", "value": "restorative"},
    )
    after = db.connection.execute(
        "SELECT projected_observation_ids, content_sha256 FROM feature_snapshots"
        " WHERE prediction_episode_id = ?",
        (result["prediction_episode_id"],),
    ).fetchone()
    assert load_list(after["projected_observation_ids"]) == before_ids
    assert after["content_sha256"] == before_hash


def test_inv_12_an_idempotent_replay_returns_the_same_resource(caregiver) -> None:
    payload = {
        "subject_id": ids.SUBJECT_ANA,
        "source": "home",
        "session_kind": "caregiver_daily",
    }
    first = caregiver.post("/api/v1/form-sessions", payload, key="inv-12")
    second = caregiver.post("/api/v1/form-sessions", payload, key="inv-12")
    assert first.json() == second.json()


def test_inv_13_no_target_means_no_episode_and_no_overlapping_primaries(caregiver, db) -> None:
    first = complete_session(caregiver)
    linked = complete_session(caregiver)
    assert linked["status"] == "episode_linked"
    with db.write() as connection:
        connection.execute(
            "UPDATE target_definition_versions SET approval_status = 'retired',"
            " retired_at = '2026-08-25T00:00:00.000Z'"
        )
    session = open_session(caregiver)
    closed = caregiver.post(f"/api/v1/form-sessions/{session['form_session_id']}/submit").json()
    assert closed["status"] == "target_definition_unavailable"
    primaries = db.connection.execute(
        "SELECT COUNT(*) AS n FROM prediction_episodes WHERE role = 'primary'"
    ).fetchone()["n"]
    assert primaries == 1
    assert first["prediction_episode_id"] == linked["linked_prediction_episode_id"]


def test_inv_14_an_early_no_stays_pending_and_the_deadline_yields_unknown(caregiver, clock) -> None:
    result = complete_session(caregiver)
    early = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert early["resolution"]["status"] == "pending"
    clock.advance(hours=49)
    episode = caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    assert episode["resolution_status"] == "unknown"
    assert episode["resolution_status"] != "no"


def test_inv_15_incompatible_reports_produce_conflicted(caregiver, clock) -> None:
    result = complete_session(caregiver)
    occurred_at = format_timestamp(parse_timestamp(result["submitted_at"]) + timedelta(hours=2))
    clock.advance(hours=25)
    report(
        caregiver,
        result["prediction_episode_id"],
        {"value": "yes", "occurred_at": occurred_at},
    )
    conflicted = report(caregiver, result["prediction_episode_id"], {"value": "no"}).json()
    assert conflicted["resolution"]["status"] == "conflicted"
    assert conflicted["resolution"]["ever_conflicted"] is True


def test_inv_27_the_api_flow_never_mutates_the_active_catalog(caregiver, db) -> None:
    """P1 prueba que el dominio no muta el catálogo; P2 prueba el flujo API."""

    def catalog_state() -> list[tuple]:
        return [
            tuple(row)
            for table in ("catalog_versions", "strategy_versions", "corpus_versions")
            for row in db.connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        ]

    before = catalog_state()
    result = complete_session(caregiver)
    caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}/recommendations")
    report(caregiver, result["prediction_episode_id"], {"value": "unknown"})
    assert catalog_state() == before


def test_inv_29_a_human_plan_shows_no_rag_citations(db) -> None:
    """La tabla de planes humanos no tiene forma de enlazar una cita."""
    columns = {
        row[1] for row in db.connection.execute("PRAGMA table_info(human_plan_versions)").fetchall()
    }
    assert "citation_id" not in columns
    assert "document_chunk_id" not in columns
    assert not any("citation" in column for column in columns)


def test_inv_30_sqlite_blocks_pilot_startup(tmp_path) -> None:
    import pytest

    from apps.api.errors import FaroApiError
    from apps.api.settings import Settings
    from apps.api.store.db import Database

    with pytest.raises(FaroApiError) as error:
        Database(Settings(mode="pilot", database_url="sqlite:///x", db_path=tmp_path / "p.db"))  # type: ignore[arg-type]
    assert error.value.code == "pilot_requires_postgresql"


def test_inv_31_cross_tenant_and_missing_grant_are_403_and_audited(
    caregiver, other_tenant_caregiver, db
) -> None:
    cross = other_tenant_caregiver.post(
        "/api/v1/form-sessions",
        {"subject_id": ids.SUBJECT_ANA, "source": "home", "session_kind": "caregiver_daily"},
    )
    same_tenant = caregiver.post(
        "/api/v1/form-sessions",
        {
            "subject_id": ids.SUBJECT_SIN_GRANT,
            "source": "home",
            "session_kind": "caregiver_daily",
        },
    )
    assert cross.status_code == 403
    assert same_tenant.status_code == 403
    reasons = {
        row["reason_code"]
        for row in db.connection.execute(
            "SELECT reason_code FROM audit_events WHERE decision = 'denied'"
        ).fetchall()
    }
    assert reasons >= {"cross_tenant", "subject_access_denied"}
