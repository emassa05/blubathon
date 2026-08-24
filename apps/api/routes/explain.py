from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import get_history
from ml.engine.explain import compute_drivers
from ml.engine.pipeline import predict_for_child
from ml.narrative import build_narrative_payload, generate_narrative
from ml.strategies.catalog import list_strategies
from ml.voi.compute import merge_today_known

router = APIRouter()

_STRATEGY_LABELS = {s["id"]: s["label_es"] for s in list_strategies()}

# El SPEC (§2) no define un campo `child_name`: los niños se identifican
# solo por `child_id` (UUID). No hay fuente de nombre real; se usa un
# término neutro en vez de inventar uno (regla §0.11, no fabricar datos).
_CHILD_NAME_PLACEHOLDER = "tu hijo o hija"


@router.get("/explain")
def explain(child_id: str, date: str, conn: sqlite3.Connection = Depends(get_db)):
    history = get_history(conn, child_id, as_of_date=date)

    result = predict_for_child(history, date)  # deja propagar _AbstainSignal

    today_known = merge_today_known(history, date)
    drivers = compute_drivers(today_known)

    payload = build_narrative_payload(
        child_name=_CHILD_NAME_PLACEHOLDER,
        risk_band=result["risk_band"],
        confidence=result["confidence"],
        drivers=drivers,
    )
    narrative, source = generate_narrative(payload)

    return {
        "drivers": [
            {
                "variable": d["variable"],
                "shap": d["shap"],
                "direction": d["direction"],
                "detail_es": d["detail_es"],
            }
            for d in drivers
        ],
        "narrative": narrative,
        "narrative_source": source,
        "strategies": [
            {"id": sid, "label_es": _STRATEGY_LABELS[sid]} for sid in payload["candidate_strategies"]
        ],
    }
