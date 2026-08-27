"""Unicode NFC and LF, applied once, so a citation can be checked literally.

SPEC 9.4 fixes the normalisation of extracted text: Unicode NFC and LF line
endings. A quote is then verified against *that* text and its locator, while the
hash of the original bytes keeps the provenance of the file the team downloaded.

Normalisation is deliberately shallow. Collapsing whitespace or stripping
punctuation would make more quotes "match", which is exactly the wrong trade:
a citation that needs help to match is not literal.
"""

from __future__ import annotations

import unicodedata
from typing import Final

NORMALIZATION_VERSION: Final = "normalize-nfc-lf-0.3.0"

_BOM: Final = "﻿"


def _to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_document_text(text: str) -> str:
    """NFC, LF line endings, no byte-order mark. Nothing else changes."""

    return unicodedata.normalize("NFC", _to_lf(text.lstrip(_BOM)))


def normalize_quote(text: str) -> str:
    """The same normalisation a chunk received, so `in` compares like with like."""

    return normalize_document_text(text)
