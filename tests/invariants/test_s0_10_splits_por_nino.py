"""§0.10 — Los splits de datos se hacen por niño, nunca por día: un niño
está entero en train, o en val, o en test.

El entrenamiento real (LightGBM, ml/synth) es zona de P1 y no existe aún.
Lo que sí es responsabilidad de P2 es que la capa de persistencia nunca
mezcle historiales entre niños: `get_history` filtra estrictamente por
`child_id`, que es la precondición para que cualquier split futuro por
niño sea siquiera posible."""

from apps.api.store.repository import get_history, insert_log


def test_s0_10_get_history_no_mezcla_ninos(db_conn):
    insert_log(
        db_conn,
        {
            "child_id": "nino_a",
            "date": "2026-08-01",
            "source": "home",
            "sleep_hours": 8.0,
            "field_provenance": {"sleep_hours": "observed"},
        },
    )
    insert_log(
        db_conn,
        {
            "child_id": "nino_b",
            "date": "2026-08-01",
            "source": "home",
            "sleep_hours": 3.0,
            "field_provenance": {"sleep_hours": "observed"},
        },
    )

    history_a = get_history(db_conn, "nino_a")
    history_b = get_history(db_conn, "nino_b")

    assert all(log["child_id"] == "nino_a" for log in history_a)
    assert all(log["child_id"] == "nino_b" for log in history_b)
    assert len(history_a) == 1 and len(history_b) == 1
