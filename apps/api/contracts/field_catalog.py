"""Re-export del catálogo de campos diarios (SPEC 5.2, 5.4, 6.7, 6.10, 7.1, 9.7).

El catálogo, su matriz de fuentes y la validación de valores viven en
`packages/shared/field_catalog.py`, que H1 publicó. `apps/**` no declara aquí
tipos, rangos ni allowlists.

Dos nombres de P2 quedaron sin equivalente y se resuelven contra P1:

- `SCENARIO_FIELD_ALLOWLIST_V1` se llama `SCENARIO_ALLOWLIST_V1` en el contrato.
- `BEHAVIOR_TAGS` era un catálogo cerrado propuesto por P2 (`R3` del README). P1
  publicó `behavior_tags` como `tag_set` con forma de token y sin enumerar el
  catálogo, que es la decisión de `SPEC 19`: una decisión ausente se registra
  como pregunta, no se inventa.
"""

from __future__ import annotations

from packages.shared.field_catalog import (
    CANONICAL_FIELD_ORDER,
    DEFAULT_ALLOWLIST_V1,
    DQI_REQUIRED_FIELDS,
    FIELD_CATALOG,
    HIGH_SIGNAL_NO_DEFAULT,
    KINDS_WITHOUT_DEFAULTS,
    MONITORED_FIELD_PRIORITY,
    MONITORED_FIELDS,
    NOTES_MAX_LENGTH,
    ORDINAL_MAXIMUM,
    ORDINAL_MINIMUM,
    SCENARIO_ALLOWLIST_V1,
    FieldSpec,
    FieldValue,
    UnknownFieldValueError,
    applicable_fields,
    closed_support,
    default_is_estimable,
    field_spec,
    sources_for,
    validate_field_value,
)

__all__ = [
    "CANONICAL_FIELD_ORDER",
    "DEFAULT_ALLOWLIST_V1",
    "DQI_REQUIRED_FIELDS",
    "FIELD_CATALOG",
    "HIGH_SIGNAL_NO_DEFAULT",
    "KINDS_WITHOUT_DEFAULTS",
    "MONITORED_FIELDS",
    "MONITORED_FIELD_PRIORITY",
    "NOTES_MAX_LENGTH",
    "ORDINAL_MAXIMUM",
    "ORDINAL_MINIMUM",
    "SCENARIO_ALLOWLIST_V1",
    "FieldSpec",
    "FieldValue",
    "UnknownFieldValueError",
    "applicable_fields",
    "closed_support",
    "default_is_estimable",
    "field_spec",
    "sources_for",
    "validate_field_value",
]
