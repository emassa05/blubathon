"""§0.6 — El missingness es una feature, nunca un cero silencioso."""

from apps.api.store.repository import get_history, insert_log


def test_s0_6_store_nunca_convierte_ausente_en_cero(db_conn):
    insert_log(
        db_conn,
        {
            "child_id": "c1",
            "date": "2026-08-01",
            "source": "home",
            "sleep_hours": 7.0,
            # dysregulation_events no se reporta.
            "field_provenance": {"sleep_hours": "observed"},
        },
    )
    history = get_history(db_conn, "c1")
    assert history[0]["dysregulation_events"] is None
    assert history[0]["crisis_occurred"] is None


def test_s0_6_crisis_occurred_null_nunca_false(db_conn):
    """Caso explícito de CONVENTIONS §7: `crisis_occurred` acepta `null` y
    nunca se convierte a `false` por omisión."""
    insert_log(
        db_conn,
        {
            "child_id": "c2",
            "date": "2026-08-01",
            "source": "home",
            "field_provenance": {},
        },
    )
    history = get_history(db_conn, "c2")
    assert history[0]["crisis_occurred"] is None
    assert history[0]["crisis_occurred"] is not False
