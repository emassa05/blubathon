"""TAREAS 2.5 — Narrativa (§10.1, §10.2)."""

from ml.narrative import build_narrative_payload, generate_narrative
from ml.narrative.llm import generate_with_llm
from ml.narrative.template import render_template


def _payload():
    drivers = [
        {
            "variable": "sleep_hours",
            "shap": 0.4,
            "direction": "empeora",
            "detail_es": "3 noches bajo su normal",
            "driver_group": "sueño",
        },
        {
            "variable": "routine_changes",
            "shap": 0.2,
            "direction": "empeora",
            "detail_es": "cambio ayer",
            "driver_group": "rutina",
        },
    ]
    return build_narrative_payload(child_name="x", risk_band="rojo", confidence="media", drivers=drivers)


def test_plantilla_produce_narrativa_valida_sin_llm():
    payload = _payload()
    narrative = render_template(payload)
    assert narrative["headline_es"]
    assert narrative["explanation_es"]
    assert isinstance(narrative["actions_es"], list)


def test_explanation_maximo_60_palabras_y_actions_maximo_3():
    payload = _payload()
    narrative = render_template(payload)
    assert len(narrative["explanation_es"].split()) <= 60
    assert len(narrative["actions_es"]) <= 3
    assert set(narrative["actions_es"]).issubset({label for label in _candidate_labels(payload)})


def _candidate_labels(payload):
    from ml.spec_constants import STRATEGIES

    return {STRATEGIES[sid] for sid in payload["candidate_strategies"]}


def test_solo_nombra_drivers_presentes_en_el_payload():
    payload = _payload()
    narrative = render_template(payload)
    present_labels = {d["label"] for d in payload["drivers"]}
    # No debe mencionar "GI" ni "sensorial/alerta": no están en el payload.
    assert "GI" not in narrative["explanation_es"]
    assert "sensorial/alerta" not in narrative["explanation_es"]
    for label in present_labels:
        assert label in narrative["explanation_es"]


def test_ollama_apagado_explain_cae_a_plantilla():
    """§10.2 — con Ollama apagado (no hay servicio en localhost:11434 en
    este entorno de test), `generate_with_llm` debe devolver `None` y
    `generate_narrative` debe caer a la plantilla, nunca reventar."""
    payload = _payload()
    assert generate_with_llm(payload) is None
    narrative, source = generate_narrative(payload)
    assert source == "template"
    assert narrative["headline_es"]
