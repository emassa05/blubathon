"""§0.9 — RANDOM_SEED=42 en todo proceso aleatorio. Dos corridas -> salida
idéntica."""

from ml.engine.pipeline import predict_for_child
from ml.voi.compute import compute_voi
from ml.voi.form import build_form


def test_s0_9_compute_voi_es_determinista(high_risk_history):
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    r1 = compute_voi(history, as_of)
    r2 = compute_voi(history, as_of)
    assert r1 == r2


def test_s0_9_build_form_es_determinista(calm_history):
    as_of = "2026-08-10"
    history = [log for log in calm_history if log["date"] <= as_of]
    f1 = build_form(history, as_of, child_id="c1", icd=0.9)
    f2 = build_form(history, as_of, child_id="c1", icd=0.9)
    assert f1 == f2


def test_s0_9_predict_es_determinista(high_risk_history):
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    r1 = predict_for_child(history, as_of)
    r2 = predict_for_child(history, as_of)
    assert r1 == r2
