"""C0 · Calidad del dato (ICD) — SPEC §5, §2.5.

Nota: `ml/features/` es zona de P1 en TAREAS.md (Hito 1.2/1.3). Como el
Hito 0 solo entrega el contrato + `baseline.py`, P2 necesita una
implementación funcional de ICD y baseline personal para poder construir
VoI, salvaguardas y formulario (§7). Esta es esa implementación mínima:
correcta contra el SPEC, sin las optimizaciones que P1 le agregaría.
"""

from __future__ import annotations

import math
from datetime import date as date_cls
from datetime import timedelta

from ml.spec_constants import (
    FIELD_RANGES,
    IMPORTANCE_WEIGHTS,
    PROVENANCE_WEIGHTS,
    RECENCY_HALF_LIFE_DAYS,
)

_COVERAGE_WINDOW_DAYS = 14
_LAMBDA = math.log(2) / RECENCY_HALF_LIFE_DAYS


def _parse_date(d: str) -> date_cls:
    return date_cls.fromisoformat(d)


def _merge_provenance_by_date(history: list[dict]) -> dict[str, dict[str, str]]:
    """Combina, por fecha, la mejor procedencia (mayor peso) de cada campo
    entre las fuentes que reportaron ese día."""
    by_date: dict[str, dict[str, str]] = {}
    for log in history:
        d = log["date"]
        prov = log.get("field_provenance", {}) or {}
        slot = by_date.setdefault(d, {})
        for field, p in prov.items():
            current = slot.get(field)
            if current is None or PROVENANCE_WEIGHTS.get(p, 0.0) > PROVENANCE_WEIGHTS.get(current, 0.0):
                slot[field] = p
    return by_date


def _coverage(by_date: dict[str, dict[str, str]], as_of: date_cls) -> float:
    window_start = as_of - timedelta(days=_COVERAGE_WINDOW_DAYS - 1)
    weight_sum = sum(IMPORTANCE_WEIGHTS.values())
    if weight_sum == 0:
        return 0.0
    total = 0.0
    for v, w in IMPORTANCE_WEIGHTS.items():
        acc = 0.0
        d = window_start
        while d <= as_of:
            prov = by_date.get(d.isoformat(), {}).get(v, "unknown")
            acc += PROVENANCE_WEIGHTS.get(prov, 0.0)
            d += timedelta(days=1)
        presencia_v = acc / _COVERAGE_WINDOW_DAYS
        total += w * presencia_v
    return total / weight_sum


def _last_registered_date(history: list[dict], as_of: date_cls) -> date_cls | None:
    anchor_fields = {"sleep_hours", "sleep_quality", "night_awakenings", "crisis_occurred"}
    best: date_cls | None = None
    for log in history:
        d = _parse_date(log["date"])
        if d > as_of:
            continue
        if any(log.get(f) is not None for f in anchor_fields):
            if best is None or d > best:
                best = d
    return best


def _recency(history: list[dict], as_of: date_cls) -> float:
    last = _last_registered_date(history, as_of)
    if last is None:
        return 0.0
    days_since = (as_of - last).days
    return math.exp(-_LAMBDA * days_since)


def _consistency(history: list[dict], as_of: date_cls) -> float:
    todays = [log for log in history if log["date"] == as_of.isoformat()]
    if len(todays) <= 1:
        return 1.0
    disagreements = []
    for field, (lo, hi) in FIELD_RANGES.items():
        values = [log.get(field) for log in todays if log.get(field) is not None]
        if len(values) < 2:
            continue
        rng = (hi - lo) or 1.0
        pairs = 0
        acc = 0.0
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                acc += abs(float(values[i]) - float(values[j])) / rng
                pairs += 1
        if pairs:
            disagreements.append(acc / pairs)
    if not disagreements:
        return 1.0
    avg_disagreement = sum(disagreements) / len(disagreements)
    return max(0.5, min(1.0, 1.0 - avg_disagreement))


def compute_icd(history: list[dict], date: str) -> dict:
    """SPEC §5.1. `history` = lista de logs (dicts estilo DailyLog) del niño."""
    as_of = _parse_date(date)
    by_date = _merge_provenance_by_date(history)
    coverage = _coverage(by_date, as_of)
    recency = _recency(history, as_of)
    consistency = _consistency(history, as_of)
    icd = coverage * recency * consistency
    return {
        "icd": icd,
        "coverage": coverage,
        "recency": recency,
        "consistency": consistency,
    }
