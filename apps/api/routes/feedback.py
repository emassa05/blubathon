from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.store.repository import insert_feedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    child_id: str
    date: str
    dysregulation_occurred: bool
    strategy_used: str | None = None
    helped: bool | None = None


@router.post("/feedback")
def feedback(body: FeedbackRequest, conn: sqlite3.Connection = Depends(get_db)):
    insert_feedback(conn, body.model_dump())
    return {"ok": True}
