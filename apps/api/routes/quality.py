from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import get_history
from ml.features.quality import compute_icd

router = APIRouter()


@router.get("/quality")
def quality(child_id: str, date: str, conn: sqlite3.Connection = Depends(get_db)):
    history = get_history(conn, child_id, as_of_date=date)
    return compute_icd(history, date)
