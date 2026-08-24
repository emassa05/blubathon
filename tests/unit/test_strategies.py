"""TAREAS 2.6 — Catálogo de estrategias (§12.1, §12.2)."""

from ml.spec_constants import DRIVER_STRATEGY_MAP, STRATEGIES
from ml.strategies.catalog import build_candidates, list_strategies


def test_10_estrategias_con_id_y_label_exactos():
    catalog = list_strategies()
    assert len(catalog) == 10
    ids = {s["id"] for s in catalog}
    assert ids == set(STRATEGIES)
    for s in catalog:
        assert s["label_es"] == STRATEGIES[s["id"]]


def test_mapeo_driver_estrategia_completo():
    expected_drivers = {"sueño", "rutina", "GI", "sensorial/alerta", "desregulación", "colegio"}
    assert set(DRIVER_STRATEGY_MAP) == expected_drivers
    all_ids = set(STRATEGIES)
    for strategies in DRIVER_STRATEGY_MAP.values():
        assert set(strategies).issubset(all_ids)


def test_build_candidates_dedup_y_max_4():
    candidates = build_candidates(["sueño", "rutina", "GI", "sensorial/alerta", "desregulación", "colegio"])
    assert len(candidates) <= 4
    assert len(candidates) == len(set(candidates))


def test_cada_driver_produce_al_menos_una_estrategia_dentro_del_catalogo():
    for driver in DRIVER_STRATEGY_MAP:
        candidates = build_candidates([driver])
        assert len(candidates) >= 1
        assert set(candidates).issubset(set(STRATEGIES))
