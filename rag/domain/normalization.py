"""Unicode NFC and LF, applied once, to every extracted document.

Fixes the normalisation of extracted text: Unicode NFC and LF line
endings, while the hash of the original bytes keeps the provenance of the file
the team downloaded.
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
