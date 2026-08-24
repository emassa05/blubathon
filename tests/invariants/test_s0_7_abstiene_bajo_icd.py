"""§0.7 — Si no hay datos suficientes, se abstiene. Nunca se fabrica un
número para rellenar."""

import pytest

from ml.engine.decision import decide, should_abstain
from ml.engine.pipeline import _AbstainSignal, predict_for_child
from ml.errors import InsufficientDataError


def test_s0_7_icd_bajo_activa_abstencion():
    assert should_abstain(icd=0.30, width=0.10, history_days=10) is True
    with pytest.raises(InsufficientDataError):
        decide(p=0.5, interval=(0.4, 0.6), icd=0.30, history_days=10)


def test_s0_7_width_alto_activa_abstencion():
    assert should_abstain(icd=0.9, width=0.61, history_days=10) is True


def test_s0_7_poca_historia_activa_abstencion():
    assert should_abstain(icd=0.9, width=0.1, history_days=4) is True


def test_s0_7_pipeline_abstiene_y_pide_variables(abstain_history):
    with pytest.raises(_AbstainSignal) as exc_info:
        predict_for_child(abstain_history, "2026-08-02")
    assert len(exc_info.value.requested_variables) > 0
    assert exc_info.value.icd is not None


def test_s0_7_abstencion_devuelve_http_200(client):
    """CONVENTIONS §6 — la abstención NO es un error HTTP."""
    resp = client.get(
        "/api/v1/predict",
        params={"child_id": "00000000-0000-0000-0000-000000000003", "date": "2026-08-02"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "insufficient_data"
    assert body["risk"] is None
    assert body["risk_band"] is None
    assert body["confidence"] is None
    assert len(body["requested_variables"]) > 0
