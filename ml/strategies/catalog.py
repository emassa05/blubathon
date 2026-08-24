"""Catálogo de estrategias — SPEC §12.1, §12.2."""

from __future__ import annotations

from ml.spec_constants import DRIVER_STRATEGY_MAP, MAX_CANDIDATE_STRATEGIES, STRATEGIES


def list_strategies() -> list[dict]:
    """SPEC §12.1 — las 10 estrategias con `id` y `label_es`."""
    return [{"id": sid, "label_es": label} for sid, label in STRATEGIES.items()]


def strategies_for_driver(driver_label: str) -> list[str]:
    """SPEC §12.2 — mapeo driver -> ids de estrategias candidatas."""
    return list(DRIVER_STRATEGY_MAP.get(driver_label, []))


def build_candidates(drivers: list[str]) -> list[str]:
    """Une los mapeos de los drivers activos, deduplica, máx 4 (§12.2)."""
    seen: list[str] = []
    for driver_label in drivers:
        for sid in strategies_for_driver(driver_label):
            if sid not in seen:
                seen.append(sid)
    return seen[:MAX_CANDIDATE_STRATEGIES]
