"""Re-export de los bytes canónicos y los hashes.

La implementación vive en `packages/shared/canonical.py`, que H1 publicó. P2 no
mantiene una segunda: dos implementaciones de la misma regla de hashing terminan
discrepando, y un hash que discrepa rompe la idempotencia y los ETag.

`parse_timestamp` se queda aquí porque no es contrato: P1 publica la forma
canónica de un instante y P2 necesita además leer de vuelta lo que persistió en
SQLite como texto.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.shared.canonical import (
    CanonicalizationError,
    bytes_hash,
    canonical_bytes,
    canonical_date,
    canonical_timestamp,
    content_hash,
    inclusive_window,
    keyed_hash,
    local_date,
    normalize_text,
    ordered_set,
    stable_bucket,
)

SCENARIO_HASH_ARTIFACT = "scenario"


def parse_timestamp(value: str) -> datetime:
    """Inversa de :func:`canonical_timestamp`, tolerante a otros offsets ISO-8601."""
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise CanonicalizationError("un timestamp persistido debe traer zona")
    return parsed.astimezone(UTC)


def canonical_json(value: object) -> str:
    """Texto JCS de un payload, para las columnas JSON de SQLite."""
    return canonical_bytes(value).decode("utf-8")


def keyed_scenario_hash(secret: bytes, schema_version: str, value: object) -> str:
    """HMAC del escenario clínico, con su separador de dominio."""
    return keyed_hash(secret, SCENARIO_HASH_ARTIFACT, schema_version, value)


__all__ = [
    "SCENARIO_HASH_ARTIFACT",
    "CanonicalizationError",
    "bytes_hash",
    "canonical_bytes",
    "canonical_date",
    "canonical_json",
    "canonical_timestamp",
    "content_hash",
    "inclusive_window",
    "keyed_hash",
    "keyed_scenario_hash",
    "local_date",
    "normalize_text",
    "ordered_set",
    "parse_timestamp",
    "stable_bucket",
]
