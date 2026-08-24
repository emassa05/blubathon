"""Hito 0 (TAREAS.md) — contrato congelado del que depende P2."""

import json
from pathlib import Path

import pytest

from ml.engine.baseline import predict_baseline
from ml.spec_constants import BAND_AMBER, BAND_RED, RANDOM_SEED
from packages.shared.models import DailyLog

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.mark.parametrize("filename", ["child_calm.json", "child_high_risk.json", "child_abstain.json"])
def test_fixtures_validan_contra_el_schema(filename):
    logs = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    assert len(logs) > 0
    for raw in logs:
        DailyLog(**raw)  # no debe lanzar


def test_predict_baseline_varia_con_sleep_hours():
    base = {
        "sleep_hours": 8.5,
        "night_awakenings": 0,
        "gi_status": 4,
        "routine_changes": False,
        "alertness": 3,
        "relevant_event_flag": False,
    }
    p_good_sleep = predict_baseline(base)
    p_bad_sleep = predict_baseline({**base, "sleep_hours": 3.0})
    assert p_bad_sleep != p_good_sleep
    assert p_bad_sleep > p_good_sleep  # menos sueño -> más riesgo


def test_constantes_de_banda_coinciden_con_el_spec():
    assert BAND_AMBER == 0.15
    assert BAND_RED == 0.35
    assert RANDOM_SEED == 42
