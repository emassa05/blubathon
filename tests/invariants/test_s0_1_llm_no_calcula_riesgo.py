"""§0.1 — El LLM nunca calcula el riesgo. Solo redacta desde un payload
que YA trae `risk_band`/`confidence` calculados por el motor determinista."""

from ml.engine.decision import band_for
from ml.narrative.template import render_template


def test_s0_1_llm_no_calcula_riesgo():
    payload = {
        "child_name": "x",
        "risk_band": "rojo",
        "risk_band_label_es": "riesgo alto",
        "confidence": "media",
        "horizon": "mañana",
        "drivers": [{"label": "sueño", "direction": "empeora", "detail": "3 noches bajo su normal"}],
        "candidate_strategies": ["advance_sleep"],
    }
    narrative = render_template(payload)

    # El schema de salida SOLO tiene texto: nunca un campo numérico de riesgo.
    assert set(narrative.keys()) == {"headline_es", "explanation_es", "actions_es"}
    assert all(isinstance(v, (str, list)) for v in narrative.values())

    # El band que aparece en la narrativa viene del motor (band_for), no del LLM.
    assert payload["risk_band"] == band_for(0.62)
    assert "riesgo alto" in narrative["headline_es"]
