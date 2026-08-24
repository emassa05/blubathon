"""Repositorio de `daily_logs` — SPEC §1, §2.5. Dueño: P2.

Capa delgada sobre SQLite. Valida el contrato de procedencia de forma
independiente de `packages.shared` (defensa en profundidad: este módulo
debe rechazar `assumed_stable` con valor aunque lo llamen sin pasar por
pydantic primero).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from ml.errors import ContractViolationError

DATA_FIELDS = (
    "sleep_hours",
    "sleep_quality",
    "night_awakenings",
    "wake_state",
    "morning_support_need",
    "gi_status",
    "food_changes",
    "routine_changes",
    "observed_behavior_note",
    "alertness",
    "dysregulation_events",
    "activity_participation",
    "social_interactions",
    "eating_status",
    "relevant_event_flag",
    "relevant_events_note",
    "crisis_occurred",
    "other_notes",
)
BOOL_FIELDS = ("food_changes", "routine_changes", "relevant_event_flag", "crisis_occurred")


def _validate_provenance(log: dict) -> None:
    """SPEC §2.5 — `assumed_stable` nunca asigna valor."""
    provenance = log.get("field_provenance") or {}
    for field, prov in provenance.items():
        if prov == "assumed_stable" and log.get(field) is not None:
            raise ContractViolationError(f"provenance_conflict: '{field}' es assumed_stable pero tiene valor")


def _row_to_log(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["observed_behavior_tags"] = json.loads(d["observed_behavior_tags"] or "[]")
    d["field_provenance"] = json.loads(d["field_provenance"] or "{}")
    for f in BOOL_FIELDS:
        if d[f] is not None:
            d[f] = bool(d[f])
    return d


def insert_log(conn: sqlite3.Connection, log: dict) -> None:
    """Idempotente por `(child_id, date, source)` (upsert)."""
    _validate_provenance(log)

    row = {f: log.get(f) for f in DATA_FIELDS}
    for f in BOOL_FIELDS:
        if row[f] is not None:
            row[f] = int(bool(row[f]))

    log_id = log.get("log_id") or f"{log['child_id']}:{log['date']}:{log['source']}"
    created_at = log.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    columns = [
        "log_id",
        "child_id",
        "date",
        "source",
        *DATA_FIELDS,
        "observed_behavior_tags",
        "capture_method",
        "field_provenance",
        "created_at",
    ]
    values = {
        "log_id": log_id,
        "child_id": log["child_id"],
        "date": log["date"],
        "source": log["source"],
        **row,
        "observed_behavior_tags": json.dumps(log.get("observed_behavior_tags") or []),
        "capture_method": log.get("capture_method", "form"),
        "field_provenance": json.dumps(log.get("field_provenance") or {}),
        "created_at": created_at,
    }

    placeholders = ", ".join(f":{c}" for c in columns)
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in columns if c != "log_id")
    conn.execute(
        f"""
        INSERT INTO daily_logs ({", ".join(columns)}) VALUES ({placeholders})
        ON CONFLICT(child_id, date, source) DO UPDATE SET {update_clause}
        """,
        values,
    )
    conn.commit()


def insert_logs(conn: sqlite3.Connection, logs: list[dict]) -> None:
    for log in logs:
        insert_log(conn, log)


def get_history(conn: sqlite3.Connection, child_id: str, as_of_date: str | None = None) -> list[dict]:
    """Historial cronológico del niño. Campos ausentes -> `None`, nunca `0`."""
    if as_of_date is not None:
        cur = conn.execute(
            "SELECT * FROM daily_logs WHERE child_id = ? AND date <= ? ORDER BY date ASC",
            (child_id, as_of_date),
        )
    else:
        cur = conn.execute("SELECT * FROM daily_logs WHERE child_id = ? ORDER BY date ASC", (child_id,))
    return [_row_to_log(row) for row in cur.fetchall()]


def list_child_ids(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT DISTINCT child_id FROM daily_logs ORDER BY child_id")
    return [row["child_id"] for row in cur.fetchall()]


def insert_feedback(conn: sqlite3.Connection, feedback: dict) -> None:
    import uuid

    conn.execute(
        """
        INSERT INTO feedback (feedback_id, child_id, date, dysregulation_occurred,
                               strategy_used, helped, created_at)
        VALUES (:feedback_id, :child_id, :date, :dysregulation_occurred,
                :strategy_used, :helped, :created_at)
        """,
        {
            "feedback_id": str(uuid.uuid4()),
            "child_id": feedback["child_id"],
            "date": feedback["date"],
            "dysregulation_occurred": int(bool(feedback["dysregulation_occurred"])),
            "strategy_used": feedback.get("strategy_used"),
            "helped": None if feedback.get("helped") is None else int(bool(feedback["helped"])),
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    conn.commit()
