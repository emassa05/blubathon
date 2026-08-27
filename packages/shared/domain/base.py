"""Shared base model, scalar types and validators for every Faro contract.

CONVENTIONS 6: `extra="forbid"` at API boundaries, UUID v4 identifiers,
timezone-aware UTC timestamps, closed enums, and an explicit model for every
response. Models are frozen because the history they describe is append-only: a
correction is a new row, never a mutated one.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from packages.shared.canonical import content_hash, local_date, normalize_text
from packages.shared.field_catalog import (
    NAMESPACED_TAG_REGEX,
    NOTES_MAX_LENGTH,
    TAG_REGEX,
)


def _to_utc(value: datetime) -> datetime:
    """Normalise an aware timestamp to UTC; a naive one is a contract error."""

    return value.astimezone(UTC)


def _normalized(value: str) -> str:
    return normalize_text(value)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
LocalDate = date

Tag = Annotated[str, StringConstraints(pattern=TAG_REGEX, max_length=64)]
NamespacedTag = Annotated[str, StringConstraints(pattern=NAMESPACED_TAG_REGEX, max_length=96)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
VersionLabel = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$"),
]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
SpanishText = Annotated[str, AfterValidator(_normalized), StringConstraints(min_length=1)]
NotesText = Annotated[
    str, AfterValidator(_normalized), StringConstraints(max_length=NOTES_MAX_LENGTH)
]


class FaroModel(BaseModel):
    """Frozen, closed contract model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
        use_enum_values=False,
        ser_json_bytes="base64",
        populate_by_name=False,
    )

    def canonical_payload(self) -> dict[str, Any]:
        """JSON-mode dump used as the input to every content hash (SPEC 5.9)."""

        return self.model_dump(mode="json", exclude_none=False)

    def compute_content_sha256(self, artifact: str, schema_version: str) -> str:
        """Domain-separated hash of this exact payload."""

        return content_hash(artifact, schema_version, self.canonical_payload())


class AppendOnlyModel(FaroModel):
    """A row that is only ever added, and corrected by appending another row.

    Concrete models set `record_id` and `record_kind`, and `effective_instant`
    when they carry a semantic time distinct from ingestion. `project_as_of`
    reads exactly these three.
    """

    tenant_id: UUID
    ingested_at: UtcDatetime
    supersedes_id: UUID | None = None

    @property
    def record_id(self) -> UUID:  # pragma: no cover - overridden by every subclass
        raise NotImplementedError

    @property
    def record_kind(self) -> str:  # pragma: no cover - overridden by every subclass
        raise NotImplementedError

    @property
    def effective_instant(self) -> datetime | None:
        return None


class Interval(FaroModel):
    """A closed probability interval. Both bounds or neither (CONVENTIONS 6)."""

    lower: Probability
    upper: Probability

    def model_post_init(self, _context: Any) -> None:
        if self.lower > self.upper:
            raise ValueError("interval lower bound exceeds its upper bound")


def derive_local_date(instant: datetime) -> date:
    """Reference-zone date of an instant, persisted with every observation."""

    return local_date(instant)


__all__ = [
    "AppendOnlyModel",
    "FaroModel",
    "Interval",
    "LocalDate",
    "NamespacedTag",
    "NonNegativeFloat",
    "NotesText",
    "Probability",
    "Sha256Hex",
    "SpanishText",
    "Tag",
    "UtcDatetime",
    "VersionLabel",
    "derive_local_date",
]
