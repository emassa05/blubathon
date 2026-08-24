"""Drivers estilo SHAP a partir de `predict_baseline` — apoya SPEC §11.3.

Cuando P1 entregue LightGBM, esto se reemplaza por SHAP real (TreeExplainer);
la forma de salida (`variable`, `shap`, `direction`, `detail_es`) no cambia.
"""

from __future__ import annotations

from ml.engine.baseline import NEED_DEFAULT, _burden
from ml.spec_constants import (
    BETA_AWAK,
    BETA_GI,
    BETA_GI_SENSORY,
    BETA_ROUTINE,
    BETA_SENSORY,
    BETA_SLEEP,
    BETA_SLEEP_ROUTINE,
    VARIABLE_LABELS_ES,
)

# variable -> driver label del §12.2 (sueño|rutina|GI|sensorial/alerta)
DRIVER_GROUP = {
    "sleep_hours": "sueño",
    "night_awakenings": "sueño",
    "gi_status": "GI",
    "routine_changes": "rutina",
    "alertness": "sensorial/alerta",
    "relevant_event_flag": "sensorial/alerta",
}


def _detail_es(variable: str, value) -> str:
    if variable == "sleep_hours" and isinstance(value, (int, float)):
        delta = NEED_DEFAULT - value
        if delta > 0:
            return f"{delta:.1f} h bajo su necesidad estimada"
        return "sobre su necesidad estimada"
    if variable == "night_awakenings":
        return f"{value} despertares nocturnos"
    if variable == "gi_status":
        return "molestias digestivas" if (value or 0) <= 2 else "sin molestias digestivas"
    if variable == "routine_changes":
        return "cambio de rutina hoy" if value else "sin cambios de rutina"
    if variable == "alertness":
        return "activación fuera de lo habitual" if value in (1, 2, 4, 5) else "activación adecuada"
    if variable == "relevant_event_flag":
        return "evento fuera de lo común hoy" if value else "sin eventos fuera de lo común"
    return VARIABLE_LABELS_ES.get(variable, variable)


def compute_drivers(features: dict, top_n: int = 3) -> list[dict]:
    """Contribuciones aditivas del latente L (§8.1) evaluadas en `features`.
    Ordenadas por |contribución| descendente, top `top_n`."""
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

    contributions = {
        "sleep_hours": BETA_SLEEP * sleep_burden + BETA_SLEEP_ROUTINE * sleep_burden * routine_load,
        "night_awakenings": BETA_AWAK * awak_burden,
        "gi_status": BETA_GI * gi_burden + BETA_GI_SENSORY * gi_burden * sensory_load,
        "routine_changes": BETA_ROUTINE * routine_load,
        # BETA_SENSORY * sensory_load repartido en sus dos componentes aditivos
        # (sensory_load = 0.6*alert_extreme + 0.4*event_load, §8.3).
        "alertness": BETA_SENSORY * 0.6 * alert_extreme,
        "relevant_event_flag": BETA_SENSORY * 0.4 * event_load,
    }

    drivers = []
    for variable, shap in sorted(contributions.items(), key=lambda kv: -abs(kv[1]))[:top_n]:
        if abs(shap) < 1e-9:
            continue
        drivers.append(
            {
                "variable": variable,
                "shap": round(shap, 4),
                "direction": "empeora" if shap > 0 else "mejora",
                "detail_es": _detail_es(variable, features.get(variable)),
                "driver_group": DRIVER_GROUP.get(variable, variable),
            }
        )
    return drivers
