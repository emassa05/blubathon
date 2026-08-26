"""Deterministic recommendation risk bands and retrieval queries."""

from __future__ import annotations

from typing import Any

from apps.api.contracts.models import AnswerItem
from packages.shared import texts
from packages.shared.enums import FieldCode
from packages.shared.field_catalog import FIELD_CATALOG
from rag.domain.text_guard import FREE_TEXT_FIELDS


def risk_band_for(probability: float | None) -> str:
    if probability is None:
        return "unknown"
    if probability >= 0.5:
        return "high"
    if probability >= 0.2:
        return "medium"
    return "low"


def query_for(probability: float | None, answers: tuple[AnswerItem, ...]) -> str:
    by_field = {
        answer.field_code: answer.value
        for answer in answers
        if answer.interaction != "unknown" and answer.field_code not in FREE_TEXT_FIELDS
    }
    parts = []
    for field_code in FIELD_CATALOG:
        code = FieldCode(field_code)
        if code not in by_field:
            continue
        parts.append(f"{texts.FIELD_LABELS_ES[code]} : {_value_label(by_field[code])}")
    band = risk_band_for(probability)
    prefix = {"high": "Riesgo alto. ", "medium": "Riesgo medio. ", "low": "Riesgo bajo. "}
    return prefix.get(band, "") + ". ".join(parts)


def _value_label(value: Any) -> str:
    mappings = (
        texts.SLEEP_QUALITY_LABELS_ES,
        texts.WAKE_STATE_LABELS_ES,
        texts.GI_STATUS_LABELS_ES,
        texts.MEDICATION_ADHERENCE_LABELS_ES,
        texts.ALERTNESS_LABELS_ES,
        texts.DAILY_REGULATION_LABELS_ES,
        texts.ATTENDANCE_LABELS_ES,
    )
    for mapping in mappings:
        for key, label in mapping.items():
            if str(key) == str(value):
                return label
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
