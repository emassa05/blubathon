"""Versioned adapters from an external export vocabulary to canonical values.

An adapter preserves the source value, uses a versioned mapping table, and fails
on a category it does not know. It never converts a category into a count or a
position on a scale (CONVENTIONS 8.4, INV-35).
"""

from ml.adapters.bluba import (
    FIELD_MAPS,
    MAPPING_VERSION,
    SEVERE_INTENSITY_BAND,
    MappedValue,
    map_value,
    mapped_fields_for,
    source_vocabulary,
)

__all__ = [
    "FIELD_MAPS",
    "MAPPING_VERSION",
    "SEVERE_INTENSITY_BAND",
    "MappedValue",
    "map_value",
    "mapped_fields_for",
    "source_vocabulary",
]
