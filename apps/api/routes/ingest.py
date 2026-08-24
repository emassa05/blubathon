from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import insert_logs
from packages.shared.models import DailyLog

router = APIRouter()


@router.post("/ingest")
def ingest(payload: DailyLog | list[DailyLog], conn: sqlite3.Connection = Depends(get_db)):
    logs = payload if isinstance(payload, list) else [payload]
    dicts = [log.model_dump() for log in logs]
    insert_logs(conn, dicts)
    last = dicts[-1]
    return {"ok": True, "child_id": last["child_id"], "date": last["date"]}
