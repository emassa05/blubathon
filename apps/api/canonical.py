"""Bytes canónicos y hashes con separación de dominio (SPEC 5.9).

P2 necesita esto para el hash de payload idempotente, los ETag de revisión y el
`content_sha256` de lo que persiste. Cuando P1 publique una implementación
canónica en `packages/shared`, este módulo se reemplaza por un re-export.

Reglas implementadas:

- Normalización Unicode NFC de todo string.
- Timestamps UTC en ``YYYY-MM-DDTHH:mm:ss.sssZ``.
- Serialización RFC 8785 (JCS): claves ordenadas por unidades de código UTF-16,
  sin espacios en blanco, escapes mínimos.
- ``SHA256("faro:<artifact>:<schema_version>\\0" || canonical_bytes)``.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class CanonicalizationError(ValueError):
    """El valor no tiene una representación canónica definida."""


def format_timestamp(value: datetime) -> str:
    """SPEC 5.9: UTC con milisegundos y sufijo Z."""
    if value.tzinfo is None:
        raise CanonicalizationError("un timestamp canónico debe ser consciente de zona")
    moment = value.astimezone(UTC)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{moment.microsecond // 1000:03d}Z"


def parse_timestamp(value: str) -> datetime:
    """Inversa de :func:`format_timestamp` tolerante a otros offsets ISO-8601."""
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise CanonicalizationError("un timestamp persistido debe traer zona")
    return parsed.astimezone(UTC)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _escape(text: str) -> str:
    out = ['"']
    for char in _nfc(text):
        escape = _ESCAPES.get(char)
        if escape is not None:
            out.append(escape)
        elif ord(char) < 0x20:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _number(value: float | int) -> str:
    """Número al estilo ECMAScript ``Number::toString`` que exige JCS."""
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        raise CanonicalizationError("NaN e infinito no tienen forma canónica JSON")
    if value == 0:
        return "0"
    if value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    text = repr(value)
    if "e" in text or "E" in text:
        mantissa, _, exponent = text.partition("e")
        mantissa = mantissa.rstrip("0").rstrip(".") if "." in mantissa else mantissa
        sign = "+" if not exponent.startswith("-") else "-"
        digits = exponent.lstrip("+-").lstrip("0") or "0"
        return f"{mantissa}e{sign}{digits}"
    return text


def _utf16_sort_key(key: str) -> bytes:
    return _nfc(key).encode("utf-16-be", errors="surrogatepass")


def _normalize(value: Any) -> Any:
    """Reduce el valor a los tipos JSON antes de serializar."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return format_timestamp(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        # Un set no tiene orden propio: SPEC 5.9 lo ordena por valor canónico.
        return sorted((_normalize(item) for item in value), key=lambda item: canonical_json(item))
    raise CanonicalizationError(f"tipo sin forma canónica: {type(value).__name__}")


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, Mapping):
        members = sorted(value.items(), key=lambda item: _utf16_sort_key(item[0]))
        body = ",".join(f"{_escape(key)}:{_serialize(item)}" for key, item in members)
        return "{" + body + "}"
    if isinstance(value, Sequence):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise CanonicalizationError(f"tipo sin forma canónica: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Representación JCS del valor como texto."""
    return _serialize(_normalize(value))


def canonical_bytes(value: Any) -> bytes:
    """Representación JCS del valor como bytes UTF-8."""
    return canonical_json(value).encode("utf-8")


def domain_hash(artifact: str, schema_version: str, value: Any) -> str:
    """``SHA256("faro:<artifact>:<schema_version>\\0" || canonical_bytes)``."""
    prefix = f"faro:{artifact}:{schema_version}\0".encode()
    return hashlib.sha256(prefix + canonical_bytes(value)).hexdigest()


def keyed_scenario_hash(secret: bytes, schema_version: str, value: Any) -> str:
    """HMAC-SHA256 del escenario clínico (SPEC 5.9).

    El espacio de escenarios es de baja entropía, así que el hash sin clave no
    sale de la frontera clínica.
    """
    prefix = f"faro:scenario:{schema_version}\0".encode()
    return hmac.new(secret, prefix + canonical_bytes(value), hashlib.sha256).hexdigest()
