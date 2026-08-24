from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.store.repository import get_history
from ml.engine.baseline import predict_baseline
from ml.engine.decision import band_for
from ml.voi.compute import merge_today_known

router = APIRouter()


class CounterfactualRequest(BaseModel):
    child_id: str
    date: str
    overrides: dict


@router.post("/counterfactual")
def counterfactual(body: CounterfactualRequest, conn: sqlite3.Connection = Depends(get_db)):
    history = get_history(conn, body.child_id, as_of_date=body.date)
    today_known = merge_today_known(history, body.date)

    risk_before = predict_baseline(today_known)
    after_features = {**today_known, **body.overrides}
    risk_after = predict_baseline(after_features)

    return {
        "risk_before": round(risk_before, 4),
        "risk_after": round(risk_after, 4),
        "band_before": band_for(risk_before),
        "band_after": band_for(risk_after),
    }
