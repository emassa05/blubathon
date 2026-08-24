"""VoI — SPEC §7.1–§7.3, §7.6.

`compute_voi` es una función pura de `ml/`, sin HTTP ni disco (CONVENTIONS §2).
Recibe `history` (lista de logs dict, estilo DailyLog) y devuelve el ranking
de variables faltantes por valor de la información.
"""

from __future__ import annotations

import statistics
from typing import Callable

from ml.engine.baseline import predict_baseline
from ml.features.personal import personal_stats
from ml.spec_constants import (
    SUGGESTION_MIN_OBSERVATIONS,
    SUGGESTION_WINDOW_DAYS,
    VARIABLE_PROMPTS_ES,
    VERBAL_ANCHORS,
    VOI_K,
)
from ml.voi.sampling import sample_values

CANDIDATE_VARIABLES = tuple(VARIABLE_PROMPTS_ES.keys())


def merge_today_known(history: list[dict], date: str) -> dict:
    """Combina, para `date`, el mejor valor conocido de cada campo entre
    todas las fuentes que reportaron ese día (§2.3: varias fuentes por día)."""
    known: dict = {}
    for log in history:
        if log["date"] != date:
            continue
        for field in CANDIDATE_VARIABLES:
            if log.get(field) is not None and known.get(field) is None:
                known[field] = log[field]
    return known


def voi_for_variable(
    history: list[dict],
    variable: str,
    date: str,
    today_known: dict,
    k: int = VOI_K,
    model_predict: Callable[[dict], float] = predict_baseline,
) -> float:
    """SPEC §7.1: `VoI(v) = Var_k(p_k)` sobre `K` imputaciones de `v`."""
    samples = sample_values(history, variable, date, k=k)
    p_values = []
    for s in samples:
        features = dict(today_known)
        features[variable] = s
        p_values.append(model_predict(features))
    return statistics.pvariance(p_values) if len(p_values) > 1 else 0.0


def suggestion_for(history: list[dict], variable: str, date: str) -> tuple[float | int | None, str | None]:
    """SPEC §7.6: mediana personal de 14 días, solo si hay ≥5 observaciones."""
    stats = personal_stats(
        history,
        variable,
        date,
        window_days=SUGGESTION_WINDOW_DAYS,
        min_observations=SUGGESTION_MIN_OBSERVATIONS,
    )
    if not stats["sufficient"]:
        return None, None
    median = stats["median"]
    if variable in VERBAL_ANCHORS:
        rounded = int(round(median))
        rounded = max(1, min(5, rounded))
        return rounded, VERBAL_ANCHORS[variable][rounded]
    return round(median, 2), None


def compute_voi(
    history: list[dict],
    date: str,
    today_known: dict | None = None,
    k: int = VOI_K,
    model_predict: Callable[[dict], float] = predict_baseline,
) -> list[dict]:
    """SPEC §7.1–§7.3. Devuelve las variables **faltantes** el día `date`,
    ordenadas por VoI descendente. `today_known` permite el recálculo
    secuencial (§7.3): pásale lo ya respondido en la sesión."""
    known = today_known if today_known is not None else merge_today_known(history, date)
    missing = [v for v in CANDIDATE_VARIABLES if known.get(v) is None]

    results = []
    for v in missing:
        voi = voi_for_variable(history, v, date, known, k=k, model_predict=model_predict)
        suggestion, suggestion_label = suggestion_for(history, v, date)
        results.append(
            {
                "variable": v,
                "voi": voi,
                "suggestion": suggestion,
                "suggestion_label_es": suggestion_label,
            }
        )
    results.sort(key=lambda r: (-r["voi"], r["variable"]))
    return results
