"""TAREAS 2.1 — Persistencia SQLite (§1, §2.5)."""

from apps.api.store.repository import get_history, insert_log, insert_logs


def test_ingest_es_idempotente_por_child_date_source(db_conn):
    log = {
        "child_id": "c1",
        "date": "2026-08-01",
        "source": "home",
        "sleep_hours": 7.0,
        "field_provenance": {"sleep_hours": "observed"},
    }
    insert_log(db_conn, log)
    insert_log(db_conn, {**log, "sleep_hours": 8.0})  # mismo (child,date,source)

    history = get_history(db_conn, "c1")
    assert len(history) == 1
    assert history[0]["sleep_hours"] == 8.0  # se actualizó, no se duplicó


def test_distintas_fuentes_mismo_dia_no_colisionan(db_conn):
    insert_logs(
        db_conn,
        [
            {
                "child_id": "c1",
                "date": "2026-08-01",
                "source": "home",
                "sleep_hours": 7.0,
                "field_provenance": {"sleep_hours": "observed"},
            },
            {
                "child_id": "c1",
                "date": "2026-08-01",
                "source": "therapy",
                "gi_status": 4,
                "field_provenance": {"gi_status": "observed"},
            },
        ],
    )
    history = get_history(db_conn, "c1")
    assert len(history) == 2


def test_historial_orden_cronologico(db_conn):
    insert_logs(
        db_conn,
        [
            {"child_id": "c1", "date": "2026-08-03", "source": "home", "field_provenance": {}},
            {"child_id": "c1", "date": "2026-08-01", "source": "home", "field_provenance": {}},
            {"child_id": "c1", "date": "2026-08-02", "source": "home", "field_provenance": {}},
        ],
    )
    history = get_history(db_conn, "c1")
    assert [log["date"] for log in history] == ["2026-08-01", "2026-08-02", "2026-08-03"]


def test_get_history_respeta_as_of_date(db_conn):
    insert_logs(
        db_conn,
        [
            {"child_id": "c1", "date": "2026-08-01", "source": "home", "field_provenance": {}},
            {"child_id": "c1", "date": "2026-08-05", "source": "home", "field_provenance": {}},
        ],
    )
    history = get_history(db_conn, "c1", as_of_date="2026-08-02")
    assert [log["date"] for log in history] == ["2026-08-01"]
