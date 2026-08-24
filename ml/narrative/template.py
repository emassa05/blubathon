"""Plantilla determinista — SPEC §10.2. Se construye ANTES que el LLM y es
la ruta por defecto probada, no un parche de emergencia."""

from __future__ import annotations

from ml.spec_constants import NARRATIVE_MAX_ACTIONS, NARRATIVE_MAX_EXPLANATION_WORDS, STRATEGIES


def render_template(payload: dict) -> dict:
    child_name = payload["child_name"]
    band_label = payload["risk_band_label_es"]
    drivers = payload["drivers"]

    headline_es = f"{child_name}: {band_label} para {payload['horizon']}"

    if drivers:
        parts = [f"{d['label']} ({d['detail']})" for d in drivers[:3]]
        explanation_es = "El riesgo se explica principalmente por: " + "; ".join(parts) + "."
    else:
        explanation_es = (
            "No hay señales destacadas hoy; el nivel de riesgo se mantiene dentro de lo esperado."
        )

    words = explanation_es.split()
    if len(words) > NARRATIVE_MAX_EXPLANATION_WORDS:
        explanation_es = " ".join(words[:NARRATIVE_MAX_EXPLANATION_WORDS])

    actions_es = [
        STRATEGIES[sid] for sid in payload["candidate_strategies"][:NARRATIVE_MAX_ACTIONS]
    ]

    return {
        "headline_es": headline_es,
        "explanation_es": explanation_es,
        "actions_es": actions_es,
    }
