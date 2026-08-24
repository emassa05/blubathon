"""Formulario adaptativo y salvaguardas — SPEC §7.4, §7.5.

`build_form` es la función pura que arma el `VoIResponse` (§11.2). Las
salvaguardas (§7.5) están separadas para que cada una tenga su propio test.
"""

from __future__ import annotations

from ml.features.personal import (
    days_since_observed,
    personal_stats,
    robust_z_score,
)
from ml.spec_constants import (
    ANOMALY_Z_THRESHOLD,
    EXPLORATION_MODULO,
    FILTER_QUESTION_ES,
    HIGH_WEIGHT,
    HIGHLIGHTED_ICD_THRESHOLD,
    HIGHLIGHTED_SIZE_DEFAULT,
    HIGHLIGHTED_SIZE_LOW_ICD,
    IMPORTANCE_WEIGHTS,
    STALENESS_CEILING_DAYS,
    VARIABLE_PROMPTS_ES,
)
from ml.voi.compute import compute_voi, merge_today_known
from ml.voi.util import stable_hash_int

CLOSING_QUESTION_TEMPLATE_ES = "¿El {target_date} hubo una crisis o episodio de desregulación mayor?"


def _effective_dv(history: list[dict], variable: str, date: str) -> int:
    d_v = days_since_observed(history, variable, date)
    return d_v if d_v is not None else STALENESS_CEILING_DAYS + 1


def staleness_candidates(history: list[dict], date: str, missing_vars: set[str]) -> list[str]:
    """SPEC §7.5a — variables de HIGH_WEIGHT con `d_v >= 7`, tie-break
    `w_v` desc -> `d_v` desc -> alfabético."""
    candidates = [
        v
        for v in HIGH_WEIGHT
        if v in missing_vars and _effective_dv(history, v, date) >= STALENESS_CEILING_DAYS
    ]
    candidates.sort(key=lambda v: (-IMPORTANCE_WEIGHTS[v], -_effective_dv(history, v, date), v))
    return candidates


def exploration_triggered(child_id: str, date: str) -> bool:
    """SPEC §7.5c — cuota de exploración determinista."""
    return stable_hash_int(child_id + date) % EXPLORATION_MODULO == 0


def least_observed_high_weight(history: list[dict], date: str, missing_vars: set[str]) -> str | None:
    """La variable de HIGH_WEIGHT menos observada en los últimos 14 días."""
    pool = [v for v in HIGH_WEIGHT if v in missing_vars]
    if not pool:
        return None
    counts = {v: personal_stats(history, v, date, window_days=14)["n_observations"] for v in pool}
    min_count = min(counts.values())
    tied = sorted(v for v in pool if counts[v] == min_count)
    return tied[0]


def detect_anomaly(history: list[dict], date: str, today_known: dict) -> bool:
    """SPEC §7.5b — |z-score personal| >= 2.0 en alguna respuesta del día."""
    for variable, value in today_known.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        stats = personal_stats(history, variable, date)
        if not stats["sufficient"]:
            continue
        z = robust_z_score(float(value), stats["median"], stats["mad"])
        if z == z and abs(z) >= ANOMALY_Z_THRESHOLD:  # z == z descarta NaN
            return True
    return False


def _closing_block(history: list[dict], date: str) -> tuple[str | None, str | None]:
    """BLOQUE 0 — cierra el loop de la predicción de ayer si aún no se
    reportó `crisis_occurred` del día objetivo anterior (`date - 1`)."""
    from datetime import date as date_cls
    from datetime import timedelta

    target = (date_cls.fromisoformat(date) - timedelta(days=1)).isoformat()
    already_reported = any(
        log["date"] == target and log.get("crisis_occurred") is not None for log in history
    )
    if already_reported:
        return None, None
    return CLOSING_QUESTION_TEMPLATE_ES.format(target_date=target), target


def _make_item(history: list[dict], date: str, ranked: dict, reason: str) -> dict:
    variable = ranked["variable"]
    return {
        "variable": variable,
        "prompt_es": VARIABLE_PROMPTS_ES[variable],
        "voi": ranked["voi"],
        "reason": reason,
        "suggestion": ranked["suggestion"],
        "suggestion_label_es": ranked["suggestion_label_es"],
        "days_since_observed": days_since_observed(history, variable, date),
    }


def build_form(
    history: list[dict], date: str, child_id: str, icd: float, today_known: dict | None = None
) -> dict:
    """SPEC §7.4 — ensambla el `VoIResponse` completo, con salvaguardas §7.5."""
    known = today_known if today_known is not None else merge_today_known(history, date)
    ranked = compute_voi(history, date, today_known=known)
    ranked_by_var = {r["variable"]: r for r in ranked}
    missing_vars = set(ranked_by_var)

    size = HIGHLIGHTED_SIZE_LOW_ICD if icd < HIGHLIGHTED_ICD_THRESHOLD else HIGHLIGHTED_SIZE_DEFAULT
    highlighted_vars = [r["variable"] for r in ranked[:size]]
    reasons = dict.fromkeys(highlighted_vars, "voi")

    stale = staleness_candidates(history, date, missing_vars)
    for v in stale:
        if v in highlighted_vars:
            # ya estaba por VoI: igual se etiqueta como techo de antigüedad,
            # que es la razón más informativa para mostrar al usuario.
            reasons[v] = "staleness"
            continue
        if not highlighted_vars:
            break
        # desplaza la posición de MENOR VoI del bloque (§7.5a)
        weakest = min(highlighted_vars, key=lambda x: ranked_by_var[x]["voi"])
        highlighted_vars[highlighted_vars.index(weakest)] = v
        reasons.pop(weakest, None)
        reasons[v] = "staleness"

    if not stale and exploration_triggered(child_id, date):
        candidate = least_observed_high_weight(history, date, missing_vars)
        if candidate and candidate not in highlighted_vars and highlighted_vars:
            weakest = min(highlighted_vars, key=lambda x: ranked_by_var[x]["voi"])
            highlighted_vars[highlighted_vars.index(weakest)] = candidate
            reasons.pop(weakest, None)
            reasons[candidate] = "exploration"

    highlighted = [_make_item(history, date, ranked_by_var[v], reasons[v]) for v in highlighted_vars]
    tail_vars = [v for v in ranked_by_var if v not in highlighted_vars]
    tail = [_make_item(history, date, ranked_by_var[v], "voi") for v in tail_vars]

    closing_question_es, closing_target_date = _closing_block(history, date)

    return {
        "child_id": child_id,
        "date": date,
        "highlighted": highlighted,
        "filter_question_es": FILTER_QUESTION_ES,
        "tail": tail,
        "closing_question_es": closing_question_es,
        "closing_target_date": closing_target_date,
    }


def resolve_filter_no(
    history: list[dict], date: str, tail_variables: list[str], today_known: dict
) -> dict[str, str]:
    """SPEC §7.4/§7.5b — filtro en 'No': la cola recibe `assumed_stable` SIN
    valor, salvo que el gatillo por anomalía (§7.5b) la despliegue igual."""
    if detect_anomaly(history, date, today_known):
        return {}
    return {v: "assumed_stable" for v in tail_variables}
