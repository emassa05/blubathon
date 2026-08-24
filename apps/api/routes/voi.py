from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import get_history
from ml.features.quality import compute_icd
from ml.voi.form import build_form

router = APIRouter()


@router.get("/voi")
def voi(child_id: str, date: str, conn: sqlite3.Connection = Depends(get_db)):
    history = get_history(conn, child_id, as_of_date=date)
    icd = compute_icd(history, date)["icd"]
    return build_form(history, date, child_id=child_id, icd=icd)
