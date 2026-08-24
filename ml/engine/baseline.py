"""Regresión logística a mano con los coeficientes de SPEC §8.2.

Determinista, sin entrenar, microsegundos. Desbloquea a P2 (VoI, narrativa,
eval) sin depender de que P1 termine LightGBM (TAREAS.md · Hito 0).

No es una réplica exacta del generador causal (§8.1, que integra L(t-1) y
perfiles de niño): aquí no hay estado latente que arrastrar, solo el registro
del día. Es una función simplificada de las mismas variables con las mismas
direcciones y pesos, suficiente para que el VoI tenga varianza real y
testeable. Cuando P1 entregue LightGBM, se cambia el import y este módulo
queda como término de comparación obligatorio (§13).
"""

from __future__ import annotations

import math

from ml.spec_constants import (
    BETA_0,
    BETA_AWAK,
    BETA_GI,
    BETA_GI_SENSORY,
    BETA_ROUTINE,
    BETA_SENSORY,
    BETA_SLEEP,
    BETA_SLEEP_ROUTINE,
)

NEED_DEFAULT = 9.0  # horas de sueño necesarias, media poblacional (§8.4)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _burden(
    value: float | int | None, low: float, high: float, *, invert: bool = False, default: float = 0.5
) -> float:
    """Normaliza `value` a una carga en [0,1]. `None` -> `default` (neutral)."""
    if value is None:
        return default
    frac = _clip((float(value) - low) / (high - low), 0.0, 1.0)
    return (1.0 - frac) if invert else frac


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def predict_baseline(features: dict) -> float:
    """Predice `p = P(crisis_occurred(t+1))` a partir de un registro del día `t`.

    `features` acepta las claves canónicas de §2.1 (pueden faltar; se usa
    un valor neutro poblacional cuando falta la variable).
    """
    sleep_hours = features.get("sleep_hours")
    night_awakenings = features.get("night_awakenings")
    gi_status = features.get("gi_status")
    routine_changes = features.get("routine_changes")
    alertness = features.get("alertness")
    relevant_event_flag = features.get("relevant_event_flag")

    sleep_burden = _burden(sleep_hours, 3.0, NEED_DEFAULT + 2.0, invert=True)
    awak_burden = _burden(night_awakenings, 0, 8)
    gi_burden = _burden(gi_status, 1, 5, invert=True)
    routine_load = 1.0 if routine_changes is True else (0.0 if routine_changes is False else 0.3)

    alert_extreme = abs((alertness if alertness is not None else 3) - 3) / 2.0
    event_load = 1.0 if relevant_event_flag is True else (0.0 if relevant_event_flag is False else 0.15)
    sensory_load = 0.6 * alert_extreme + 0.4 * event_load

    latent = (
        BETA_0
        + BETA_SLEEP * sleep_burden
        + BETA_AWAK * awak_burden
        + BETA_GI * gi_burden
        + BETA_ROUTINE * routine_load
        + BETA_SENSORY * sensory_load
        + BETA_SLEEP_ROUTINE * sleep_burden * routine_load
        + BETA_GI_SENSORY * gi_burden * sensory_load
    )
    return _sigmoid(latent)
