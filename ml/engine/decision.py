"""C3 · Decisión y abstención — SPEC §4, §5.3, §6.

Zona formal de P1 (TAREAS 1.5). Implementación mínima necesaria para que
P2 pueda producir un `RiskResponse` completo (§11.1) sin esperar a P1;
reemplazable sin tocar `ml/voi`, `ml/narrative` ni `ml/eval`.
"""

from __future__ import annotations

import math

from ml.errors import InsufficientDataError
from ml.spec_constants import (
    ABSTAIN_ICD,
    ABSTAIN_MIN_HISTORY_DAYS,
    ABSTAIN_WIDTH,
    BAND_AMBER,
    BAND_RED,
    CONFIDENCE_HIGH_ICD,
    CONFIDENCE_HIGH_WIDTH,
    CONFIDENCE_MED_ICD,
    CONFIDENCE_MED_WIDTH,
    INTERVAL_Z,
)


def band_for(p: float) -> str:
    """SPEC §4 — bordes: `<0.15` verde · `[0.15,0.35)` ámbar · `>=0.35` rojo."""
    if p < BAND_AMBER:
        return "verde"
    if p < BAND_RED:
        return "ambar"
    return "rojo"


def confidence_for(icd: float, width: float) -> str | None:
    """SPEC §5.3. Devuelve `None` si ni siquiera alcanza el piso de abstención."""
    if icd >= CONFIDENCE_HIGH_ICD and width <= CONFIDENCE_HIGH_WIDTH:
        return "alta"
    if icd >= CONFIDENCE_MED_ICD and width <= CONFIDENCE_MED_WIDTH:
        return "media"
    if icd >= ABSTAIN_ICD and width <= ABSTAIN_WIDTH:
        return "baja"
    return None


def should_abstain(icd: float, width: float, history_days: int) -> bool:
    """SPEC §6 — al menos una de las tres condiciones."""
    return icd < ABSTAIN_ICD or width > ABSTAIN_WIDTH or history_days < ABSTAIN_MIN_HISTORY_DAYS


def ensemble_predict(
    features: dict, predict_fn, seeds: tuple[int, ...]
) -> tuple[float, float, tuple[float, float]]:
    """SPEC §9.3 simplificado: como `predict_fn` (baseline) es determinista,
    no hay variación real entre semillas todavía (eso llega con el bootstrap
    real de LightGBM en P1). Se perturba levemente y de forma determinista
    por semilla para tener un `width` no-nulo y testeable mientras tanto."""
    preds = []
    for seed in seeds:
        jitter = ((seed * 2654435761) % 1000) / 1000.0 - 0.5  # determinista
        p = predict_fn(features)
        preds.append(min(1.0, max(0.0, p + jitter * 0.02)))
    mean = sum(preds) / len(preds)
    variance = sum((x - mean) ** 2 for x in preds) / len(preds)
    sigma = math.sqrt(variance)
    lo = max(0.0, mean - INTERVAL_Z * sigma)
    hi = min(1.0, mean + INTERVAL_Z * sigma)
    return mean, sigma, (lo, hi)


def decide(*, p: float, interval: tuple[float, float], icd: float, history_days: int) -> dict:
    """Combina §4/§5.3/§6 en la forma de `RiskResponse` (sin envolver HTTP)."""
    width = interval[1] - interval[0]
    if should_abstain(icd, width, history_days):
        raise InsufficientDataError("icd, width o historia insuficientes (§6)")
    return {
        "risk": round(p, 4),
        "risk_band": band_for(p),
        "interval": (round(interval[0], 4), round(interval[1], 4)),
        "confidence": confidence_for(icd, width),
        "icd": round(icd, 4),
    }
