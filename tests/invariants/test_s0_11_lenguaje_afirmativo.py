"""§0.11 — Lenguaje afirmativo y no diagnóstico. Nunca "conducta problema",
nunca "diagnóstico", nunca alarmismo."""

from ml.narrative.template import render_template
from ml.spec_constants import STRATEGIES, VARIABLE_LABELS_ES, VARIABLE_PROMPTS_ES

FORBIDDEN_TERMS = (
    "diagnóstico",
    "diagnostica",
    "conducta problema",
    "trastorno",
    "enfermo",
    "anormal",
    "peligro",
    "alarma",
)


def _assert_no_forbidden(text: str):
    lowered = text.lower()
    for term in FORBIDDEN_TERMS:
        assert term not in lowered, f"término no permitido '{term}' en: {text}"


def test_s0_11_prompts_y_labels_sin_lenguaje_prohibido():
    for text in (*VARIABLE_PROMPTS_ES.values(), *VARIABLE_LABELS_ES.values(), *STRATEGIES.values()):
        _assert_no_forbidden(text)


def test_s0_11_narrativa_plantilla_sin_lenguaje_prohibido():
    payload = {
        "child_name": "x",
        "risk_band": "rojo",
        "risk_band_label_es": "riesgo alto",
        "horizon": "mañana",
        "drivers": [{"label": "sueño", "direction": "empeora", "detail": "3 noches bajo su normal"}],
        "candidate_strategies": ["advance_sleep", "co_regulation"],
    }
    narrative = render_template(payload)
    _assert_no_forbidden(narrative["headline_es"])
    _assert_no_forbidden(narrative["explanation_es"])
    for action in narrative["actions_es"]:
        _assert_no_forbidden(action)
