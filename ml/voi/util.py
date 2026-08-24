"""Utilidades compartidas de ml/voi — hash estable SPEC §7.5c."""

from __future__ import annotations

import hashlib


def stable_hash_int(s: str) -> int:
    """SHA-256 de `s`, primeros 8 bytes como entero (big-endian)."""
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")
