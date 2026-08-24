"""The closed strategy catalogue and its driver mapping (SPEC 12.1, 12.2)."""

from __future__ import annotations

from ml.spec_constants import (
    DRIVER_STRATEGY_MAP,
    NARRATIVE_MAX_CANDIDATE_STRATEGIES,
    STRATEGIES,
)


def list_strategies() -> list[dict]:
    """Every strategy the system may ever propose, in catalogue order."""
    return [{"id": sid, "label_es": label} for sid, label in STRATEGIES.items()]


def strategies_for_driver(driver_label: str) -> list[str]:
    """The strategies a given driver licenses (SPEC 12.2)."""
    return list(DRIVER_STRATEGY_MAP.get(driver_label, []))


def build_candidates(drivers: list[str]) -> list[str]:
    """Union the active drivers' strategies, deduplicated and capped (SPEC 12.2)."""
    seen: list[str] = []
    for driver_label in drivers:
        for sid in strategies_for_driver(driver_label):
            if sid not in seen:
                seen.append(sid)
    return seen[:NARRATIVE_MAX_CANDIDATE_STRATEGIES]


def strategy_label(strategy_id: str) -> str:
    """The frozen Spanish label for a strategy id."""
    return STRATEGIES[strategy_id]
