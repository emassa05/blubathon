"""Construcción del `NarrativePayload` — SPEC §10.1."""

from __future__ import annotations

from ml.strategies.catalog import build_candidates
from packages.shared import BAND_LABELS_ES


def build_narrative_payload(
    *, child_name: str, risk_band: str, confidence: str | None, drivers: list[dict]
) -> dict:
    driver_entries = [
        {
            "label": d["driver_group"],
            "direction": d["direction"],
            "detail": d["detail_es"],
        }
        for d in drivers
    ]
    candidate_strategies = build_candidates([d["driver_group"] for d in drivers])
    return {
        "child_name": child_name,
        "risk_band": risk_band,
        "risk_band_label_es": BAND_LABELS_ES[risk_band],
        "confidence": confidence,
        "horizon": "mañana",
        "drivers": driver_entries,
        "candidate_strategies": candidate_strategies,
    }
