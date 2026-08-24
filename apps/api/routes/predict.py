from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import get_history
from ml.engine.pipeline import _AbstainSignal, predict_for_child
from ml.spec_constants import MODEL_VERSION

router = APIRouter()


@router.get("/predict")
def predict(child_id: str, date: str, conn: sqlite3.Connection = Depends(get_db)):
    history = get_history(conn, child_id, as_of_date=date)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = predict_for_child(history, date)
    except _AbstainSignal as abstain:
        return {
            "child_id": child_id,
            "date": abstain.target_date,
            "status": "insufficient_data",
            "risk": None,
            "risk_band": None,
            "interval": None,
            "confidence": None,
            "icd": abstain.icd,
            "requested_variables": abstain.requested_variables,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
        }
    return {
        "child_id": child_id,
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
        **result,
    }
