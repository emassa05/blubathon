"""Cifrado local del escenario mínimo dentro de la frontera clínica.

El objetivo en la demo es que el payload no quede legible en el archivo SQLite
ni en un dump accidental. No sustituye a un gestor de claves: el piloto usa el
cifrado institucional y una clave rotable. El escenario nunca sale
de aquí sin `AuthoringUseAuthorization`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.api.canonical import canonical_bytes


def _keystream(key: bytes, length: int) -> bytes:
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
        counter += 1
    return stream[:length]


def seal(payload: dict[str, Any], key: bytes) -> bytes:
    plaintext = canonical_bytes(payload)
    return bytes(a ^ b for a, b in zip(plaintext, _keystream(key, len(plaintext)), strict=True))


def unseal(blob: bytes, key: bytes) -> dict[str, Any] | None:
    try:
        plaintext = bytes(a ^ b for a, b in zip(blob, _keystream(key, len(blob)), strict=True))
        value = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
