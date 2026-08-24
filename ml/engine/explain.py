"""Per-variable drivers behind one prediction (SPEC 11.3).

LightGBM computes exact TreeSHAP contributions natively, so no extra dependency
is needed. Each variable owns several feature columns -- its raw value, its
personal z-score, its rolling means, its trend -- and a person cares about the
variable, not the column. Contributions are therefore summed back per variable
before ranking.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from ml.engine.model import RiskEnsemble
from ml.errors import ModelNotReadyError
from ml.spec_constants import (
    MEDICATION_ADHERENCE_CODES,
    MODEL_INPUT_FIELDS,
    NARRATIVE_MAX_ACTIONS,
    ORDINAL_MAX,
    RISK_API_DECIMALS,
)
from packages.shared import ORDINAL_ANCHORS_ES, VARIABLE_LABELS_ES

# SPEC 12.2 groups variables into the drivers that select strategies.
DRIVER_GROUPS = {
    "sleep_hours": "sueño",
    "sleep_quality": "sueño",
    "night_awakenings": "sueño",
    "wake_state": "sueño",
    "morning_support_need": "rutina",
    "routine_changes": "rutina",
    "relevant_event_flag": "rutina",
    "gi_status": "GI",
    "food_changes": "GI",
    "eating_status": "GI",
    "medication_adherence": "medicación",
    "alertness": "sensorial/alerta",
    "dysregulation_events": "desregulación",
    "activity_participation": "colegio",
    "social_interactions": "colegio",
}

_MEDICATION_LABELS = {code: name for name, code in MEDICATION_ADHERENCE_CODES.items()}


def _column_owner(column: str) -> str | None:
    """Map a feature column back to the contract variable it derives from."""
    for variable in MODEL_INPUT_FIELDS:
        if column == variable or column.startswith(f"{variable}_"):
            return variable
    return None


def contributions_by_variable(
    ensemble: RiskEnsemble,
    row: pd.DataFrame,
) -> dict[str, float]:
    """Average TreeSHAP contributions across the ensemble, summed per variable."""
    if not ensemble.is_fitted:
        raise ModelNotReadyError("the risk ensemble has not been fitted")
    features = row[ensemble.feature_names_]
    stacked = np.mean(
        [member.model.predict(features, pred_contrib=True) for member in ensemble.members_],
        axis=0,
    )
    # The final column is the expected value, not a feature contribution.
    per_column = stacked[0][: len(ensemble.feature_names_)]
    totals: dict[str, float] = {}
    for column, contribution in zip(ensemble.feature_names_, per_column, strict=True):
        variable = _column_owner(column)
        if variable is None:
            continue
        totals[variable] = totals.get(variable, 0.0) + float(contribution)
    return totals


def _detail_es(variable: str, value: Any) -> str:
    """Say what was actually recorded, in the frozen wording of SPEC 12.5."""
    label = VARIABLE_LABELS_ES.get(variable, variable)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return f"{label} sin registrar"
    if variable in ORDINAL_ANCHORS_ES:
        level = min(max(round(float(value)), 1), ORDINAL_MAX)
        anchor = ORDINAL_ANCHORS_ES[variable].get(level, "")
        return anchor.split(" — ")[0].lower() if anchor else label
    if variable == "medication_adherence":
        return {
            "taken": "tomó su medicación",
            "missed": "no tomó su medicación",
            "not_applicable": "sin medicación indicada",
        }.get(_MEDICATION_LABELS.get(int(float(value)), ""), label)
    if variable == "sleep_hours":
        return f"{float(value):.1f} h de sueño"
    if variable == "night_awakenings":
        return f"{int(value)} despertares nocturnos"
    if variable == "dysregulation_events":
        return f"{int(value)} episodios de desregulación"
    if variable in {"routine_changes", "food_changes", "relevant_event_flag"}:
        affirmative = {
            "routine_changes": ("cambio de rutina hoy", "sin cambios de rutina"),
            "food_changes": ("cambios en la alimentación", "sin cambios en la alimentación"),
            "relevant_event_flag": ("algo fuera de lo común hoy", "sin eventos fuera de lo común"),
        }[variable]
        return affirmative[0] if bool(value) else affirmative[1]
    return label


def compute_drivers(
    ensemble: RiskEnsemble,
    row: pd.DataFrame,
    answers: Mapping[str, Any] | None = None,
    top_n: int = NARRATIVE_MAX_ACTIONS,
) -> list[dict[str, Any]]:
    """Return the strongest drivers for one prediction, largest effect first.

    ``direction`` reads from the family's point of view: "empeora" means this
    variable pushed the risk up. Variables with no measurable effect are left
    out rather than padded, so the narrative can only name real causes.
    """
    totals = contributions_by_variable(ensemble, row)
    known = dict(answers or {})
    drivers = []
    for variable, contribution in sorted(totals.items(), key=lambda item: -abs(item[1])):
        if abs(contribution) < 10**-RISK_API_DECIMALS:
            continue
        value = known.get(variable)
        if value is None and variable in row.columns:
            value = row.iloc[0][variable]
        drivers.append(
            {
                "variable": variable,
                "shap": round(float(contribution), RISK_API_DECIMALS),
                "direction": "empeora" if contribution > 0 else "mejora",
                "detail_es": _detail_es(variable, value),
                "driver_group": DRIVER_GROUPS.get(variable, "sensorial/alerta"),
            }
        )
        if len(drivers) == top_n:
            break
    return drivers
