"""Orquesta C0+C1+C2+C3 en una función pura — apoya `/predict` (§11).

Zona formal de P1 (`ml/engine/`). Implementación mínima para que P2 pueda
probar el flujo completo de punta a punta mientras el LightGBM real no
existe; ver nota en `ml/engine/baseline.py`.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta

from ml.engine.baseline import predict_baseline
from ml.engine.decision import decide, ensemble_predict
from ml.errors import InsufficientDataError
from ml.features.personal import history_days_count
from ml.features.quality import compute_icd
from ml.spec_constants import (
    ENSEMBLE_SEEDS,
    HIGHLIGHTED_ICD_THRESHOLD,
    HIGHLIGHTED_SIZE_DEFAULT,
    HIGHLIGHTED_SIZE_LOW_ICD,
)
from ml.voi.compute import merge_today_known
from ml.voi.form import build_form


def predict_for_child(history: list[dict], as_of_date: str) -> dict:
    """Predice `crisis_occurred(as_of_date + 1)` usando datos hasta `as_of_date`
    inclusive (regla anti-leakage §0.2, §3).

    Devuelve un dict listo para `RiskResponse` (sin `child_id`/`model_version`/
    `generated_at`, que agrega la capa API) con `date` = el día objetivo (t+1).
    Lanza `InsufficientDataError` si corresponde abstenerse (§6); el caller
    (apps/api) la traduce en `status="insufficient_data"` con HTTP 200.
    """
    target_date = (date_cls.fromisoformat(as_of_date) + timedelta(days=1)).isoformat()
    history_days = history_days_count(history, as_of_date)
    icd_result = compute_icd(history, as_of_date)
    today_known = merge_today_known(history, as_of_date)

    p, _sigma, interval = ensemble_predict(today_known, predict_baseline, ENSEMBLE_SEEDS)

    try:
        decision = decide(p=p, interval=interval, icd=icd_result["icd"], history_days=history_days)
    except InsufficientDataError:
        requested = _requested_variables(history, as_of_date, icd_result["icd"], today_known)
        raise _AbstainSignal(requested, target_date, icd_result["icd"]) from None

    form = build_form(history, as_of_date, child_id="", icd=icd_result["icd"], today_known=today_known)
    requested_variables = [
        {"variable": item["variable"], "prompt_es": item["prompt_es"], "voi": round(item["voi"], 4)}
        for item in form["highlighted"]
    ]
    return {
        "status": "ok",
        "date": target_date,
        **decision,
        "requested_variables": requested_variables,
    }


class _AbstainSignal(InsufficientDataError):
    """Excepción que ya trae adjuntas las `requested_variables` de §6."""

    def __init__(self, requested_variables: list[dict], target_date: str, icd: float):
        super().__init__("insufficient_data")
        self.requested_variables = requested_variables
        self.target_date = target_date
        self.icd = round(icd, 4)


def _requested_variables(history: list[dict], date: str, icd: float, today_known: dict) -> list[dict]:
    size = HIGHLIGHTED_SIZE_LOW_ICD if icd < HIGHLIGHTED_ICD_THRESHOLD else HIGHLIGHTED_SIZE_DEFAULT
    form = build_form(history, date, child_id="", icd=icd, today_known=today_known)
    items = form["highlighted"][:size] or form["tail"][:size]
    return [
        {"variable": it["variable"], "prompt_es": it["prompt_es"], "voi": round(it["voi"], 4)} for it in items
    ]
