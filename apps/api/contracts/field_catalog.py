"""Catálogo de los 19 campos diarios y sus matrices (SPEC 5.2, 5.4, 6.7, 6.10, 7.1, 9.7).

PROVISIONAL - PUERTO HACIA P1 (ver ``apps/api/contracts/__init__.py``).

El catálogo define tipo, rango y fuentes permitidas. La validación de una
respuesta vive aquí porque es contrato, no estadística: ninguna función de este
módulo estima nada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from apps.api.contracts.constants import BEHAVIOR_TAG_CATALOG_VERSION
from apps.api.contracts.enums import Source

FieldType = Literal["float", "int", "enum", "ordinal", "bool", "enum_set", "text"]

ORDINAL_MIN = 1
ORDINAL_MAX = 5
NOTES_MAX_LENGTH = 500

# `behavior_tags` usa un catálogo cerrado versionado (SPEC 5.2). El SPEC no
# enumera sus valores: esta lista es una propuesta P2 marcada como pendiente de
# contrato P1 y se sustituye cuando P1 publique el catálogo.
BEHAVIOR_TAGS: tuple[str, ...] = (
    "self_regulation_attempt",
    "sensory_seeking",
    "sensory_avoiding",
    "communication_attempt",
    "routine_disruption",
    "other",
)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    field_code: str
    field_type: FieldType
    values: tuple[Any, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None
    sources: tuple[Source, ...] = ()
    default_enabled: bool = False


def _f(
    code: str,
    field_type: FieldType,
    *,
    values: tuple[Any, ...] | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    sources: tuple[Source, ...],
    default_enabled: bool = False,
) -> FieldSpec:
    return FieldSpec(code, field_type, values, minimum, maximum, sources, default_enabled)


_HOME = (Source.HOME,)
_HOME_THERAPY = (Source.HOME, Source.THERAPY)
_HOME_SCHOOL = (Source.HOME, Source.SCHOOL)
_THERAPY_SCHOOL = (Source.THERAPY, Source.SCHOOL)
_ALL = (Source.HOME, Source.THERAPY, Source.SCHOOL)

FIELD_CATALOG: dict[str, FieldSpec] = {
    spec.field_code: spec
    for spec in (
        _f("sleep_hours", "float", minimum=0.0, maximum=16.0, sources=_HOME),
        _f(
            "sleep_quality",
            "enum",
            values=("restorative", "interrupted", "sleep_onset_difficulty", "other"),
            sources=_HOME,
        ),
        _f("night_awakenings", "int", minimum=0, maximum=15, sources=_HOME),
        _f(
            "wake_state",
            "enum",
            values=("calm_happy", "tired_sleepy", "irritable_crying", "other"),
            sources=_HOME,
        ),
        _f("morning_support_need", "ordinal", minimum=1, maximum=5, sources=_HOME),
        _f(
            "gi_status",
            "enum",
            values=("normal", "constipation", "diarrhea", "other"),
            sources=_HOME_THERAPY,
        ),
        _f(
            "medication_adherence",
            "enum",
            values=("taken", "missed", "not_applicable"),
            sources=_HOME_THERAPY,
        ),
        _f("food_changes", "bool", sources=_HOME, default_enabled=True),
        _f("routine_changes", "bool", sources=_HOME),
        _f(
            "alertness",
            "enum",
            values=("low", "calm", "optimal", "high", "other"),
            sources=_ALL,
        ),
        _f("dysregulation_event_count", "int", minimum=0, maximum=20, sources=_ALL),
        _f(
            "daily_regulation_state",
            "enum",
            values=("excellent", "stable_with_support", "frequent_dysregulation", "other"),
            sources=_ALL,
        ),
        _f(
            "activity_participation",
            "ordinal",
            minimum=1,
            maximum=5,
            sources=_ALL,
            default_enabled=True,
        ),
        _f(
            "social_interactions",
            "ordinal",
            minimum=1,
            maximum=5,
            sources=_ALL,
            default_enabled=True,
        ),
        _f(
            "eating_status",
            "ordinal",
            minimum=1,
            maximum=5,
            sources=_HOME_SCHOOL,
            default_enabled=True,
        ),
        _f(
            "attendance_status",
            "enum",
            values=("present", "absent", "not_applicable"),
            sources=_THERAPY_SCHOOL,
            default_enabled=True,
        ),
        _f("relevant_event_flag", "bool", sources=_ALL),
        _f("behavior_tags", "enum_set", values=BEHAVIOR_TAGS, sources=_ALL),
        _f("notes", "text", maximum=NOTES_MAX_LENGTH, sources=_ALL),
    )
}

# Orden canónico del catálogo (SPEC 6.9 paso 5). Es el orden de declaración.
CANONICAL_FIELD_ORDER: tuple[str, ...] = tuple(FIELD_CATALOG)

# SPEC 6.7. Todo campo ausente tiene defaults deshabilitados.
DEFAULT_ALLOWLIST_V1: tuple[str, ...] = tuple(
    code for code, spec in FIELD_CATALOG.items() if spec.default_enabled
)

# SPEC 6.10. Campos monitoreados y su prioridad de desempate.
MONITORED_FIELD_PRIORITY: dict[str, int] = {
    "sleep_quality": 1,
    "wake_state": 2,
    "gi_status": 3,
    "medication_adherence": 4,
    "daily_regulation_state": 5,
}
MONITORED_FIELDS: tuple[str, ...] = tuple(MONITORED_FIELD_PRIORITY)

# SPEC 7.1. Los cinco campos del denominador de coverage.
DQI_REQUIRED_FIELDS: tuple[str, ...] = MONITORED_FIELDS

# SPEC 9.7. Allowlist v1 de `build_scenario`.
SCENARIO_FIELD_ALLOWLIST_V1: tuple[str, ...] = (
    "sleep_quality",
    "alertness",
    "gi_status",
    "medication_adherence",
    "daily_regulation_state",
)

# SPEC 6.7. Alta señal, sin default.
HIGH_SIGNAL_WITHOUT_DEFAULT: tuple[str, ...] = (
    "sleep_quality",
    "wake_state",
    "gi_status",
    "medication_adherence",
    "routine_changes",
    "alertness",
    "daily_regulation_state",
    "dysregulation_event_count",
    "relevant_event_flag",
)


class FieldValueError(ValueError):
    """Un valor que el catálogo no admite. Nunca se degrada a `null` (SPEC 5.3)."""

    def __init__(self, field_code: str, reason: str) -> None:
        super().__init__(f"{field_code}: {reason}")
        self.field_code = field_code
        self.reason = reason


def applicable_fields(source: Source) -> tuple[str, ...]:
    """Campos habilitados para la fuente de la sesión (SPEC 5.4)."""
    return tuple(code for code, spec in FIELD_CATALOG.items() if source in spec.sources)


def is_applicable(field_code: str, source: Source) -> bool:
    spec = FIELD_CATALOG.get(field_code)
    return spec is not None and source in spec.sources


def validate_value(field_code: str, value: Any) -> Any:
    """Normaliza y valida un valor contra el catálogo. Falla cerrado."""
    spec = FIELD_CATALOG.get(field_code)
    if spec is None:
        raise FieldValueError(field_code, "campo desconocido")
    if value is None:
        raise FieldValueError(field_code, "un valor observado no puede ser null")

    if spec.field_type == "bool":
        if not isinstance(value, bool):
            raise FieldValueError(field_code, "se esperaba true o false")
        return value
    if isinstance(value, bool):
        raise FieldValueError(field_code, "se esperaba un valor no booleano")

    if spec.field_type == "float":
        if not isinstance(value, (int, float)):
            raise FieldValueError(field_code, "se esperaba un número")
        number = float(value)
        if spec.minimum is not None and number < spec.minimum:
            raise FieldValueError(field_code, f"menor que {spec.minimum}")
        if spec.maximum is not None and number > spec.maximum:
            raise FieldValueError(field_code, f"mayor que {spec.maximum}")
        return number
    if spec.field_type in ("int", "ordinal"):
        if not isinstance(value, int):
            raise FieldValueError(field_code, "se esperaba un entero")
        if spec.minimum is not None and value < spec.minimum:
            raise FieldValueError(field_code, f"menor que {int(spec.minimum)}")
        if spec.maximum is not None and value > spec.maximum:
            raise FieldValueError(field_code, f"mayor que {int(spec.maximum)}")
        return value
    if spec.field_type == "enum":
        if value not in (spec.values or ()):
            raise FieldValueError(field_code, "categoría fuera del catálogo cerrado")
        return value
    if spec.field_type == "enum_set":
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise FieldValueError(field_code, "se esperaba una lista de tags")
        allowed = set(spec.values or ())
        unknown = [item for item in value if item not in allowed]
        if unknown:
            raise FieldValueError(
                field_code,
                f"tags fuera de {BEHAVIOR_TAG_CATALOG_VERSION}: {sorted(unknown)}",
            )
        return sorted(set(value))
    if spec.field_type == "text":
        if not isinstance(value, str):
            raise FieldValueError(field_code, "se esperaba texto")
        if spec.maximum is not None and len(value) > int(spec.maximum):
            raise FieldValueError(field_code, f"excede {int(spec.maximum)} caracteres")
        return value
    raise FieldValueError(field_code, "tipo de campo no soportado")  # pragma: no cover
