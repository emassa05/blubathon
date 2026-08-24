"""§0.5 — Nunca se imputa para el modelo. La imputación vive SOLO en VoI
(§7.1-7.2); el modelo de riesgo nunca ve valores imputados."""

from ml.voi.compute import merge_today_known


def test_s0_5_merge_today_known_no_imputa(abstain_history):
    """`merge_today_known` (lo que ve el motor de riesgo) solo contiene lo
    reportado ese día. Un campo que nadie tocó no aparece con un valor
    inventado: sigue ausente hasta que se responde."""
    as_of = "2026-08-02"  # solo trae crisis_occurred; sleep_hours no fue tocado
    history_upto_t = [log for log in abstain_history if log["date"] <= as_of]
    known = merge_today_known(history_upto_t, as_of)

    assert known.get("sleep_hours") is None
    assert "sleep_hours" not in known or known["sleep_hours"] is None


def test_s0_5_prediccion_nunca_llama_al_muestreador(monkeypatch, high_risk_history):
    """El path de `/predict` (fuera de VoI) nunca invoca el muestreador de
    imputaciones de §7.2."""
    import ml.voi.sampling as sampling

    called = {"n": 0}
    original = sampling.sample_values

    def spy(*args, **kwargs):
        called["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(sampling, "sample_values", spy)

    as_of = "2026-08-05"
    history_upto_t = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history_upto_t, as_of)
    from ml.engine.baseline import predict_baseline

    predict_baseline(known)

    assert called["n"] == 0
