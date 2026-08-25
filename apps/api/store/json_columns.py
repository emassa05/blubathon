"""Lectura y escritura de columnas JSON validadas (CONVENTIONS 13)."""

from __future__ import annotations

import json
from typing import Any

from apps.api.canonical import canonical_json


def dump(value: Any) -> str:
    """Serializa en bytes canónicos: dos escrituras iguales dan el mismo texto."""
    return canonical_json(value)


def load(raw: str | None, default: Any = None) -> Any:
    if raw is None or raw == "":
        return default
    return json.loads(raw)


def load_list(raw: str | None) -> list[Any]:
    value = load(raw, [])
    if not isinstance(value, list):
        raise ValueError("se esperaba una lista JSON en la columna")
    return value


def load_dict(raw: str | None) -> dict[str, Any]:
    value = load(raw, {})
    if not isinstance(value, dict):
        raise ValueError("se esperaba un objeto JSON en la columna")
    return value
