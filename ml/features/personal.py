"""C1 · Baseline personal (n-of-1) — SPEC §9.1.

Igual que `quality.py`: implementación mínima funcional para desbloquear a
P2 (VoI §7.2 necesita mediana/MAD personal; las salvaguardas §7.5 necesitan
`days_since_observed` y el z-score de anomalía). Zona formal de P1.
"""

from __future__ import annotations

import math
from datetime import date as date_cls
from datetime import timedelta

_MAD_TO_SD = 1.4826  # factor de escala para que MAD ~ desviación estándar


def _parse_date(d: str) -> date_cls:
    return date_cls.fromisoformat(d)


def _observed_values(history: list[dict], variable: str, as_of: date_cls, window_days: int) -> list[float]:
    window_start = as_of - timedelta(days=window_days - 1)
    out = []
    for log in history:
        d = _parse_date(log["date"])
        if window_start <= d <= as_of and log.get(variable) is not None:
            prov = (log.get("field_provenance") or {}).get(variable, "observed")
            if prov in ("observed", "confirmed"):
                out.append(float(log[variable]))
    return out


def robust_stats(values: list[float]) -> tuple[float, float]:
    """Mediana y MAD (median absolute deviation) de `values`."""
    if not values:
        return math.nan, math.nan
    sorted_v = sorted(values)
    n = len(sorted_v)
    mid = n // 2
    median = sorted_v[mid] if n % 2 else (sorted_v[mid - 1] + sorted_v[mid]) / 2
    deviations = sorted([abs(v - median) for v in values])
    m = len(deviations)
    mid2 = m // 2
    mad = deviations[mid2] if m % 2 else (deviations[mid2 - 1] + deviations[mid2]) / 2
    return median, mad


def personal_stats(
    history: list[dict], variable: str, as_of_date: str, window_days: int = 30, min_observations: int = 5
) -> dict:
    """Mediana/MAD personal de `variable` en la ventana que termina en `as_of_date`."""
    as_of = _parse_date(as_of_date)
    values = _observed_values(history, variable, as_of, window_days)
    median, mad = robust_stats(values)
    return {
        "median": median,
        "mad": mad,
        "n_observations": len(values),
        "sufficient": len(values) >= min_observations,
    }


def robust_z_score(value: float, median: float, mad: float) -> float:
    """z-score robusto. `NaN` si no hay suficiente base (nunca 0, SPEC §9.1)."""
    if math.isnan(median) or math.isnan(mad):
        return math.nan
    scale = mad * _MAD_TO_SD
    if scale == 0:
        return 0.0 if value == median else math.copysign(float("inf"), value - median)
    return (value - median) / scale


def days_since_observed(history: list[dict], variable: str, as_of_date: str) -> int | None:
    """`d_v` de SPEC §7.2: días desde la última observación con
    provenance ∈ {observed, confirmed}. `None` si nunca se observó."""
    as_of = _parse_date(as_of_date)
    best: date_cls | None = None
    for log in history:
        d = _parse_date(log["date"])
        if d > as_of or log.get(variable) is None:
            continue
        prov = (log.get("field_provenance") or {}).get(variable, "observed")
        if prov not in ("observed", "confirmed"):
            continue
        if best is None or d > best:
            best = d
    if best is None:
        return None
    return (as_of - best).days


def history_days_count(history: list[dict], as_of_date: str) -> int:
    """Días de historia distintos con al menos un registro, hasta `as_of_date`."""
    as_of = _parse_date(as_of_date)
    days = {log["date"] for log in history if _parse_date(log["date"]) <= as_of}
    return len(days)
