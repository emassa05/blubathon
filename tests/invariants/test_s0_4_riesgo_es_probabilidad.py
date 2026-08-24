"""§0.4 — El riesgo canónico es `p ∈ [0,1]`. La UI muestra `round(p*100)`
como entero; el porcentaje nunca se guarda como fuente."""

from ml.engine.baseline import predict_baseline
from ml.engine.decision import decide


def test_s0_4_riesgo_en_0_1():
    p = predict_baseline({"sleep_hours": 8.5, "night_awakenings": 0})
    assert 0.0 <= p <= 1.0


def test_s0_4_ui_percentage_es_entero_derivado():
    decision = decide(p=0.6234, interval=(0.5, 0.7), icd=0.9, history_days=10)
    assert 0.0 <= decision["risk"] <= 1.0
    ui_percent = round(decision["risk"] * 100)
    assert isinstance(ui_percent, int)
    assert ui_percent == 62
