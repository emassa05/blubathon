"""Canonical bytes, hashes and local calendar windows.

Two artifacts that mean the same thing must hash the same, and two that differ
must not. That requires one normalisation everybody shares: Unicode NFC,
millisecond UTC timestamps, RFC 8785 (JCS) serialisation, sorted set-like
arrays, and a domain separator so a document hash can never collide with a
strategy hash.

The clinical scenario hash is different on purpose: the space of scenarios is
small enough to enumerate, so it uses HMAC with a tenant secret and never leaves
the clinical boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo

import rfc8785

from packages.shared.constants import REFERENCE_TIMEZONE

REFERENCE_ZONE: Final = ZoneInfo(REFERENCE_TIMEZONE)
TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%f"
HASH_DOMAIN_PREFIX: Final = "blubathon"


class CanonicalizationError(ValueError):
    """A payload cannot be canonicalised, so it cannot be hashed."""


def normalize_text(value: str) -> str:
    """Unicode NFC. Two spellings of the same string must not hash differently."""

    return unicodedata.normalize("NFC", value)


def canonical_timestamp(value: datetime) -> str:
    """`YYYY-MM-DDTHH:mm:ss.sssZ` in UTC, always with milliseconds."""

    if value.tzinfo is None:
        raise CanonicalizationError("a naive datetime has no canonical form")
    moment = value.astimezone(UTC)
    return f"{moment.strftime(TIMESTAMP_FORMAT)[:-3]}Z"


def canonical_date(value: date) -> str:
    """`YYYY-MM-DD`. A `datetime` is rejected: a date is a different decision."""

    if isinstance(value, datetime):
        raise CanonicalizationError("use local_date() to derive a date from an instant")
    return value.isoformat()


def local_date(instant: datetime, zone: ZoneInfo = REFERENCE_ZONE) -> date:
    """Reference-zone calendar date of an instant.

    Persisted alongside every observation so a window stays reproducible even if
    a timezone library later changes.
    """

    if instant.tzinfo is None:
        raise CanonicalizationError("a naive datetime has no local date")
    return instant.astimezone(zone).date()


def inclusive_window(cutoff_date: date, days: int) -> tuple[date, date]:
    """Last `W` calendar days, inclusive: `[D-(W-1), D]`."""

    if days < 1:
        raise CanonicalizationError("an inclusive window needs at least one day")
    return cutoff_date - timedelta(days=days - 1), cutoff_date


def exclusive_window(cutoff_date: date, days: int) -> tuple[date, date]:
    """Previous `W` calendar days, excluding `D`: `[D-W, D)`.

    The returned upper bound is the last day *inside* the window, so a caller
    compares with `<=` in both directions.
    """

    if days < 1:
        raise CanonicalizationError("an exclusive window needs at least one day")
    return cutoff_date - timedelta(days=days), cutoff_date - timedelta(days=1)


def in_window(value: date, window: tuple[date, date]) -> bool:
    start, end = window
    return start <= value <= end


def ordered_set(values: Iterable[str]) -> list[str]:
    """Deduplicate and sort a set-like array before serialisation.

    Arrays with ranking semantics keep their order and must not pass through
    here.
    """

    return sorted({normalize_text(value) for value in values})


def _canonicalize(value: Any) -> Any:
    """Normalise strings and reject anything JCS cannot represent faithfully."""

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError("NaN and infinity have no canonical JSON form")
        return value
    if isinstance(value, datetime):
        return canonical_timestamp(value)
    if isinstance(value, date):
        return canonical_date(value)
    if isinstance(value, Mapping):
        return {normalize_text(str(key)): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise CanonicalizationError(
            "a set has no declared order; call ordered_set() and pass a list"
        )
    raise CanonicalizationError(f"{type(value).__name__} has no canonical JSON form")


def canonical_bytes(payload: Any) -> bytes:
    """RFC 8785 (JCS) bytes of an already-normalised payload."""

    try:
        return rfc8785.dumps(_canonicalize(payload))
    except rfc8785.CanonicalizationError as error:  # pragma: no cover - defensive
        raise CanonicalizationError(str(error)) from error


def domain_separator(artifact: str, schema_version: str) -> bytes:
    """`blubathon:<artifact>:<schema_version>\\0`."""

    prefix = f"{HASH_DOMAIN_PREFIX}:{artifact}:{schema_version}"
    return normalize_text(prefix).encode("utf-8") + b"\x00"


def content_hash(artifact: str, schema_version: str, payload: Any) -> str:
    """Domain-separated SHA-256 of a canonical payload, as lowercase hex."""

    digest = hashlib.sha256()
    digest.update(domain_separator(artifact, schema_version))
    digest.update(canonical_bytes(payload))
    return digest.hexdigest()


def bytes_hash(payload: bytes) -> str:
    """Plain SHA-256 of raw bytes, used for document provenance."""

    return hashlib.sha256(payload).hexdigest()


def keyed_hash(secret: bytes, artifact: str, schema_version: str, payload: Any) -> str:
    """HMAC-SHA256 for low-entropy clinical payloads such as a scenario.

    An unkeyed hash of a scenario would be enumerable, so it stays inside the
    clinical boundary and the keyed digest is what gets stored.
    """

    if not secret:
        raise CanonicalizationError("a keyed hash needs a tenant secret")
    message = domain_separator(artifact, schema_version) + canonical_bytes(payload)
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def stable_bucket(secret: bytes, parts: Sequence[str], modulus: int) -> int:
    """HMAC bucket assignment used by audit mode and exploration.

    The client cannot predict it, and it never changes for the same inputs.
    """

    if modulus < 1:
        raise CanonicalizationError("a bucket modulus must be positive")
    if not secret:
        raise CanonicalizationError("a bucket assignment needs a secret")
    message = "|".join(normalize_text(part) for part in parts).encode("utf-8")
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return int.from_bytes(digest, "big") % modulus
