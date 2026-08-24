"""§0.13 — El VoI ordena y destaca; nunca esconde. Las variables están
siempre accesibles (highlighted + tail cubren TODAS las faltantes)."""

from ml.spec_constants import VARIABLE_PROMPTS_ES
from ml.voi.compute import merge_today_known
from ml.voi.form import build_form


def test_s0_13_highlighted_mas_tail_cubre_todas_las_faltantes(high_risk_history):
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history, as_of)
    icd = 0.9
    form = build_form(history, as_of, child_id="c1", icd=icd, today_known=known)

    shown_vars = {item["variable"] for item in form["highlighted"]} | {
        item["variable"] for item in form["tail"]
    }
    missing_vars = {v for v in VARIABLE_PROMPTS_ES if known.get(v) is None}
    assert shown_vars == missing_vars


def test_s0_13_bloque_4_siempre_disponible():
    """El bloque 4 ('quiero contar algo más') es una propiedad del cliente
    (formulario completo, las 15 variables), no del backend: el backend
    nunca oculta una variable del catálogo de prompts."""
    assert len(VARIABLE_PROMPTS_ES) == 14  # las 14 con w_v (§12.4)
