"""§0.2 — Sin fuga temporal. Barajar/mutar los valores del día t+1 no debe
cambiar ninguna predicción de t+1 hecha con historia hasta t."""

import copy

from ml.engine.pipeline import predict_for_child


def test_s0_2_sin_leakage(high_risk_history):
    as_of = "2026-08-05"
    history_upto_t = [log for log in high_risk_history if log["date"] <= as_of]

    result_a = predict_for_child(copy.deepcopy(history_upto_t), as_of)

    # Agrego un día t+1 (y más allá) con valores extremos, opuestos al resto.
    mutated = copy.deepcopy(history_upto_t)
    future_log = copy.deepcopy(high_risk_history[-1])
    future_log["date"] = "2026-08-06"
    future_log["sleep_hours"] = 0.0
    future_log["crisis_occurred"] = True
    future_log["gi_status"] = 1
    mutated.append(future_log)

    result_b = predict_for_child(mutated, as_of)

    assert result_a["risk"] == result_b["risk"]
    assert result_a["risk_band"] == result_b["risk_band"]
