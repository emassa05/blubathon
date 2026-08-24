"""§0.8 — Toda predicción viaja con `confidence` + `icd`. Un riesgo sin
confianza no se muestra (si no hay confianza asignable, se abstiene)."""

from ml.engine.decision import confidence_for, decide


def test_s0_8_ok_siempre_trae_confidence_e_icd():
    decision = decide(p=0.5, interval=(0.45, 0.55), icd=0.8, history_days=10)
    assert decision["confidence"] is not None
    assert decision["icd"] is not None


def test_s0_8_confidence_none_bajo_el_piso_es_coherente_con_abstencion():
    # Si confidence_for no puede asignar ninguna etiqueta, should_abstain
    # ya habría disparado antes (mismos umbrales de ICD/width, §5.3 vs §6).
    assert confidence_for(icd=0.20, width=0.10) is None
