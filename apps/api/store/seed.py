"""Fill the demo database from every source the project has (SPEC 8.7).

Three sources, three purposes. The synthetic cohort is what the model was
trained and measured on. The Bluba export is what makes the demo real: four
actual cases, with their real gaps. The fixtures keep three hand-written
children with known shapes for the tests.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from apps.api.store.db import get_connection, init_db
from apps.api.store.repository import insert_logs
from ml.adapters.bluba import build_bluba_logs

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = _REPOSITORY_ROOT / "fixtures"
BLUBA_DIR = _REPOSITORY_ROOT / "Datos base"
DATA_DIR = _REPOSITORY_ROOT / "data"

BLUBA_DAILY_FILE = "4_seguimiento_diario_tutor.csv"
BLUBA_SESSIONS_FILE = "3_sesiones_profesionales.csv"
BLUBA_EVENTS_FILE = "5_eventos_desregulacion_tutor.csv"
# Bluba exports semicolon-separated CSV with a byte-order mark.
_CSV_ENCODING = "utf-8-sig"
_CSV_DELIMITER = ";"


def _null_safe(value: Any) -> Any:
    """Parquet hands back pandas NA and numpy arrays; SQLite wants None and lists."""
    if isinstance(value, np.ndarray):
        return list(value)
    if value is None or (not isinstance(value, list | tuple) and pd.isna(value)):
        return None
    return value


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding=_CSV_ENCODING, newline="") as handle:
        return list(csv.DictReader(handle, delimiter=_CSV_DELIMITER))


def seed_from_fixtures(conn, fixtures_dir: Path = FIXTURES_DIR) -> int:
    """Load the hand-written fixture children."""
    total = 0
    for path in sorted(fixtures_dir.glob("*.json")):
        logs = json.loads(path.read_text(encoding="utf-8"))
        insert_logs(conn, logs)
        total += len(logs)
    return total


def seed_from_bluba(conn, bluba_dir: Path = BLUBA_DIR) -> int:
    """Load the four anonymised Bluba cases through the canonical adapter."""
    daily = _read_csv(bluba_dir / BLUBA_DAILY_FILE)
    if not daily:
        return 0
    logs = build_bluba_logs(
        daily,
        _read_csv(bluba_dir / BLUBA_SESSIONS_FILE),
        _read_csv(bluba_dir / BLUBA_EVENTS_FILE),
    )
    insert_logs(conn, logs)
    return len(logs)


def seed_from_parquet(conn, data_dir: Path = DATA_DIR, limit_children: int | None = None) -> int:
    """Load the synthetic cohort the model was trained on."""
    logs_path = data_dir / "logs.parquet"
    if not logs_path.exists():
        return 0
    frame = pd.read_parquet(logs_path)
    if limit_children is not None:
        keep = sorted(frame["child_id"].unique())[:limit_children]
        frame = frame[frame["child_id"].isin(keep)]
    records = [
        {key: _null_safe(value) for key, value in record.items()}
        for record in frame.to_dict("records")
    ]
    insert_logs(conn, records)
    return len(records)


def seed_all(
    conn=None,
    *,
    fixtures_dir: Path = FIXTURES_DIR,
    bluba_dir: Path = BLUBA_DIR,
    data_dir: Path = DATA_DIR,
    limit_children: int | None = None,
) -> dict[str, int]:
    """Seed every available source, reporting how many rows each contributed."""
    owned = conn is None
    connection = conn if conn is not None else get_connection()
    init_db(connection)
    try:
        return {
            "fixtures": seed_from_fixtures(connection, fixtures_dir),
            "bluba": seed_from_bluba(connection, bluba_dir),
            "synthetic": seed_from_parquet(connection, data_dir, limit_children),
        }
    finally:
        if owned:
            connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Faro demo database")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--limit-children",
        type=int,
        default=None,
        help="only load this many synthetic children, to keep the demo database small",
    )
    args = parser.parse_args()
    counts = seed_all(data_dir=args.data_dir, limit_children=args.limit_children)
    for source, rows in counts.items():
        print(f"  {source}: {rows} registros")
    print(f"total: {sum(counts.values())}")


if __name__ == "__main__":
    main()
