"""§4 — Bordes exactos de banda: el clásico bug `<` vs `<=`."""

from ml.engine.decision import band_for


def test_s4_bordes_de_banda():
    assert band_for(0.1499) == "verde"
    assert band_for(0.15) == "ambar"
    assert band_for(0.3499) == "ambar"
    assert band_for(0.35) == "rojo"
