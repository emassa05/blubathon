"""SQLite connection and schema (SPEC 1, 2.5).

All persistence lives here: ``ml/`` never touches disk (CONVENTIONS 2).
The column list mirrors DailyLog field for field, so a contract change that
forgets this file fails loudly on insert instead of silently dropping data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "faro.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_logs (
    log_id                  TEXT PRIMARY KEY,
    child_id                TEXT NOT NULL,
    date                    TEXT NOT NULL,
    source                  TEXT NOT NULL,
    sleep_hours              REAL,
    sleep_quality             INTEGER,
    night_awakenings          INTEGER,
    wake_state                INTEGER,
    morning_support_need      INTEGER,
    gi_status                 INTEGER,
    medication_adherence      TEXT,
    food_changes               INTEGER,
    routine_changes            INTEGER,
    observed_behavior_tags    TEXT,
    observed_behavior_note    TEXT,
    alertness                  INTEGER,
    dysregulation_events       INTEGER,
    activity_participation     INTEGER,
    social_interactions        INTEGER,
    eating_status               INTEGER,
    relevant_event_flag        INTEGER,
    relevant_events_note      TEXT,
    crisis_occurred             INTEGER,
    other_notes                 TEXT,
    capture_method              TEXT NOT NULL,
    field_provenance           TEXT NOT NULL,
    created_at                  TEXT,
    UNIQUE(child_id, date, source)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id            TEXT PRIMARY KEY,
    child_id                TEXT NOT NULL,
    date                    TEXT NOT NULL,
    dysregulation_occurred    INTEGER NOT NULL,
    strategy_used              TEXT,
    helped                      INTEGER,
    created_at                  TEXT
);
"""


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
