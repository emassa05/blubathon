"""Siembra `faro.db` — SPEC §8.7.

El SPEC pide sembrar desde `data/logs.parquet`, generado por `ml/synth`
(§8, zona P1, no construida aún). Mientras tanto, esta siembra usa los
`fixtures/*.json` del Hito 0 para que la app arranque con datos de
demostración. Cuando exista `logs.parquet`, se agrega `seed_from_parquet`
sin tocar `insert_logs` ni el resto del store.
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.api.store.db import get_connection, init_db
from apps.api.store.repository import insert_logs

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def seed_from_fixtures(conn=None, fixtures_dir: Path = FIXTURES_DIR) -> int:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    init_db(conn)
    total = 0
    for path in sorted(fixtures_dir.glob("*.json")):
        logs = json.loads(path.read_text(encoding="utf-8"))
        insert_logs(conn, logs)
        total += len(logs)
    if own_conn:
        conn.close()
    return total


if __name__ == "__main__":
    n = seed_from_fixtures()
    print(f"Sembrados {n} registros en data/faro.db")
