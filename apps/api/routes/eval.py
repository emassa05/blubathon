"""GET /eval — SPEC §13.

Nota de alcance: la evaluación de referencia (200 niños × 180 días,
`fairness_sex`, ablaciones §13.1/§13.2 completas) requiere `ml/synth`
(§8), zona de P1 aún no construida — el sexo del niño, en particular, es
un atributo del generador y no viaja en `DailyLog` (§2.1). Este endpoint
calcula honestamente lo que SÍ se puede derivar de los datos disponibles
en `data/faro.db` (aquí, los fixtures del Hito 0) y marca el resto como
no disponible en vez de inventar un número.
"""

from __future__ import annotations

import sqlite3
from datetime import date as date_cls
from datetime import timedelta

from fastapi import APIRouter, Depends

from apps.api.deps import get_db
from apps.api.store.repository import get_history, list_child_ids
from ml.engine.pipeline import _AbstainSignal, predict_for_child
from ml.eval.metrics import (
    baseline_always_base_rate,
    baseline_yesterday_dysregulation,
    decision_coverage,
    evaluate,
)

router = APIRouter()


def _daterange(history: list[dict]) -> list[str]:
    dates = sorted({log["date"] for log in history})
    return dates[:-1]  # el último día no tiene t+1 observable


def _actual_crisis(history: list[dict], target_date: str) -> bool | None:
    for log in history:
        if log["date"] == target_date and log.get("crisis_occurred") is not None:
            return bool(log["crisis_occurred"])
    return None


@router.get("/eval")
def eval_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    y_true: list[int] = []
    y_score: list[float] = []
    statuses: list[str] = []
    dysregulation_yesterday: list[bool] = []

    for child_id in list_child_ids(conn):
        full_history = get_history(conn, child_id)
        for as_of in _daterange(full_history):
            target = (date_cls.fromisoformat(as_of) + timedelta(days=1)).isoformat()
            actual = _actual_crisis(full_history, target)
            if actual is None:
                continue
            history_upto = [log for log in full_history if log["date"] <= as_of]
            try:
                result = predict_for_child(history_upto, as_of)
                statuses.append("ok")
                y_true.append(int(actual))
                y_score.append(result["risk"])
            except _AbstainSignal:
                statuses.append("insufficient_data")
                continue
            today_log = next((log for log in history_upto if log["date"] == as_of), {})
            dysregulation_yesterday.append(bool(today_log.get("dysregulation_events") or 0))

    metrics = (
        evaluate(y_true, y_score)
        if y_true
        else {
            "auc_pr": None,
            "auc_roc": None,
            "brier": None,
            "ece": None,
            "lead_time_hours": 24,
        }
    )
    metrics["decision_coverage"] = decision_coverage(statuses)
    metrics["n_evaluated"] = len(y_true)

    baselines = {}
    if y_true:
        base_rate_scores = baseline_always_base_rate(y_true)
        baselines["always_base_rate"] = evaluate(y_true, base_rate_scores)
        if len(dysregulation_yesterday) == len(y_true):
            yest_scores = baseline_yesterday_dysregulation(dysregulation_yesterday)
            baselines["yesterday_dysregulation"] = evaluate(y_true, yest_scores)

    return {
        "metrics": metrics,
        "baselines": baselines,
        "fairness_sex": "not_available: 'sex' no viaja en DailyLog (§2.1); requiere ml/synth (§8, P1)",
        "elicitation_ablation": (
            "not_available: requiere ml/synth (§8, P1) para generar logs bajo cada política"
        ),
        "misspecification": "not_available: requiere ml/synth (§8, P1) con parámetros perturbados",
    }
