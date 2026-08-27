"""The one exception to the free-text veto, enforced (SPEC 2.23, INV-22).

Only versioned, rights-cleared literature may be chunked, indexed or placed in
an authoring prompt. Notes, messages and anything a caregiver or professional
typed never enter that pipeline, and neither do identifiers: no tenant, subject,
actor, episode or instance id reaches a chunk, an embedding or a prompt.

The guard is deliberately blunt. It refuses on the presence of an unauthorised
provenance or of a known clinical string, rather than trying to detect personal
data by inspection, which is not something a regular expression can do.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from packages.shared.enums import FieldCode, FieldKind
from packages.shared.field_catalog import FIELD_CATALOG

LITERATURE: Final = "literature"

# SPEC 5.2: the free-text and tag fields of a daily observation. None of them
# may ever become a chunk, an embedding input or prompt content.
FREE_TEXT_FIELDS: Final[frozenset[FieldCode]] = frozenset(
    code for code, spec in FIELD_CATALOG.items() if spec.kind in {FieldKind.TEXT, FieldKind.TAG_SET}
)


class FreeTextLeakError(ValueError):
    """Clinical or user-written text reached a place only literature may go."""


@dataclass(frozen=True, slots=True)
class TextProvenance:
    """A string with where it came from, carried as far as the index or prompt."""

    text: str
    kind: str
    document_version_id: UUID | None = None

    @property
    def is_literature(self) -> bool:
        return self.kind == LITERATURE and self.document_version_id is not None


def literature(text: str, document_version_id: UUID) -> TextProvenance:
    """Mark a string as coming from an authorised, versioned document."""

    return TextProvenance(text=text, kind=LITERATURE, document_version_id=document_version_id)


def assert_literature_only(
    items: Iterable[TextProvenance], *, authorised: frozenset[UUID]
) -> tuple[TextProvenance, ...]:
    """Every string must be literature from a document version in the corpus."""

    checked = tuple(items)
    for item in checked:
        if not item.is_literature:
            raise FreeTextLeakError(
                f"text of kind {item.kind!r} cannot be chunked, embedded or prompted (SPEC 2.23)"
            )
        if item.document_version_id not in authorised:
            raise FreeTextLeakError(
                "text from an unauthorised document version cannot enter the index or a prompt"
            )
    return checked


def assert_no_clinical_text(payload: str, *, sentinels: Iterable[str]) -> None:
    """Refuse a payload that carries any known clinical string or identifier.

    The caller supplies the sentinels it knows about: the notes it holds, the
    identifiers of the case it is working on. A hit means the pipeline leaked,
    and the build stops rather than being cleaned up afterwards.
    """

    for sentinel in sentinels:
        if sentinel and sentinel in payload:
            raise FreeTextLeakError(
                "a clinical identifier or free-text fragment reached an authoring payload"
            )
