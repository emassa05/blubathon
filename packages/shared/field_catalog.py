"""The 19 daily fields, their legal values and which sources may report them.

This is the catalogue SPEC 5.2 and SPEC 5.4 describe. Changing the source matrix
requires a new contract version, and the frontend only shows fields enabled for
the session's source.

Nothing here converts a category into a number. `stable_with_support` is not a
count, `present` is not a participation score, and a nominal value never becomes
an ordered scale (SPEC 5.3, INV-35).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from packages.shared.enums import (
    Alertness,
    AttendanceStatus,
    DailyRegulationState,
    FieldCode,
    FieldKind,
    GiStatus,
    MedicationAdherence,
    SleepQuality,
    Source,
    WakeState,
)

ORDINAL_MINIMUM: Final = 1
ORDINAL_MAXIMUM: Final = 5
NOTES_MAX_LENGTH: Final = 500

# A closed-catalogue token. The catalogue *contents* (care modes, sensory and
# communication tags, contraindications, behaviour tags, context tags) are
# versioned data that SPEC v0.3.0 does not enumerate, so the contract fixes the
# shape and refuses free text, without inventing clinical vocabulary (SPEC 19).
TAG_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")
NAMESPACED_TAG_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")
TAG_REGEX: Final = TAG_PATTERN.pattern
NAMESPACED_TAG_REGEX: Final = NAMESPACED_TAG_PATTERN.pattern

_ALL_SOURCES = frozenset(Source)
_HOME_ONLY = frozenset({Source.HOME})
_HOME_THERAPY = frozenset({Source.HOME, Source.THERAPY})
_HOME_SCHOOL = frozenset({Source.HOME, Source.SCHOOL})
_THERAPY_SCHOOL = frozenset({Source.THERAPY, Source.SCHOOL})


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One daily field: what it accepts, who may report it, whether it defaults."""

    code: FieldCode
    kind: FieldKind
    allowed_sources: frozenset[Source]
    default_allowed: bool
    enum_type: type[StrEnum] | None = None
    minimum: float | None = None
    maximum: float | None = None
    max_length: int | None = None

    @property
    def legal_range(self) -> float | None:
        """Span used to normalise a numeric disagreement in the DQI (SPEC 7.1)."""

        if self.minimum is None or self.maximum is None:
            return None
        return float(self.maximum) - float(self.minimum)

    def allows(self, source: Source) -> bool:
        return source in self.allowed_sources

    def allowed_values(self) -> tuple[str, ...] | None:
        """Closed support of a nominal field, in declaration order."""

        if self.enum_type is None:
            return None
        return tuple(member.value for member in self.enum_type)


# Declaration order is the canonical catalogue order used to fill remaining
# slots once outcome, staleness, exploration and VoI have had their turn.
_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        code=FieldCode.SLEEP_HOURS,
        kind=FieldKind.CONTINUOUS,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
        minimum=0.0,
        maximum=16.0,
    ),
    FieldSpec(
        code=FieldCode.SLEEP_QUALITY,
        kind=FieldKind.NOMINAL,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
        enum_type=SleepQuality,
    ),
    FieldSpec(
        code=FieldCode.NIGHT_AWAKENINGS,
        kind=FieldKind.COUNT,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
        minimum=0,
        maximum=15,
    ),
    FieldSpec(
        code=FieldCode.WAKE_STATE,
        kind=FieldKind.NOMINAL,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
        enum_type=WakeState,
    ),
    FieldSpec(
        code=FieldCode.MORNING_SUPPORT_NEED,
        kind=FieldKind.ORDINAL,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
        minimum=ORDINAL_MINIMUM,
        maximum=ORDINAL_MAXIMUM,
    ),
    FieldSpec(
        code=FieldCode.GI_STATUS,
        kind=FieldKind.NOMINAL,
        allowed_sources=_HOME_THERAPY,
        default_allowed=False,
        enum_type=GiStatus,
    ),
    FieldSpec(
        code=FieldCode.MEDICATION_ADHERENCE,
        kind=FieldKind.NOMINAL,
        allowed_sources=_HOME_THERAPY,
        default_allowed=False,
        enum_type=MedicationAdherence,
    ),
    FieldSpec(
        code=FieldCode.FOOD_CHANGES,
        kind=FieldKind.BOOLEAN,
        allowed_sources=_HOME_ONLY,
        default_allowed=True,
    ),
    FieldSpec(
        code=FieldCode.ROUTINE_CHANGES,
        kind=FieldKind.BOOLEAN,
        allowed_sources=_HOME_ONLY,
        default_allowed=False,
    ),
    FieldSpec(
        code=FieldCode.ALERTNESS,
        kind=FieldKind.NOMINAL,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
        enum_type=Alertness,
    ),
    FieldSpec(
        code=FieldCode.DYSREGULATION_EVENT_COUNT,
        kind=FieldKind.COUNT,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
        minimum=0,
        maximum=20,
    ),
    FieldSpec(
        code=FieldCode.DAILY_REGULATION_STATE,
        kind=FieldKind.NOMINAL,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
        enum_type=DailyRegulationState,
    ),
    FieldSpec(
        code=FieldCode.ACTIVITY_PARTICIPATION,
        kind=FieldKind.ORDINAL,
        allowed_sources=_ALL_SOURCES,
        default_allowed=True,
        minimum=ORDINAL_MINIMUM,
        maximum=ORDINAL_MAXIMUM,
    ),
    FieldSpec(
        code=FieldCode.SOCIAL_INTERACTIONS,
        kind=FieldKind.ORDINAL,
        allowed_sources=_ALL_SOURCES,
        default_allowed=True,
        minimum=ORDINAL_MINIMUM,
        maximum=ORDINAL_MAXIMUM,
    ),
    FieldSpec(
        code=FieldCode.EATING_STATUS,
        kind=FieldKind.ORDINAL,
        allowed_sources=_HOME_SCHOOL,
        default_allowed=True,
        minimum=ORDINAL_MINIMUM,
        maximum=ORDINAL_MAXIMUM,
    ),
    FieldSpec(
        code=FieldCode.ATTENDANCE_STATUS,
        kind=FieldKind.NOMINAL,
        allowed_sources=_THERAPY_SCHOOL,
        default_allowed=True,
        enum_type=AttendanceStatus,
    ),
    FieldSpec(
        code=FieldCode.RELEVANT_EVENT_FLAG,
        kind=FieldKind.BOOLEAN,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
    ),
    FieldSpec(
        code=FieldCode.BEHAVIOR_TAGS,
        kind=FieldKind.TAG_SET,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
    ),
    FieldSpec(
        code=FieldCode.NOTES,
        kind=FieldKind.TEXT,
        allowed_sources=_ALL_SOURCES,
        default_allowed=False,
        max_length=NOTES_MAX_LENGTH,
    ),
)

FIELD_CATALOG: Final[MappingProxyType[FieldCode, FieldSpec]] = MappingProxyType(
    {spec.code: spec for spec in _FIELDS}
)
CANONICAL_FIELD_ORDER: Final[tuple[FieldCode, ...]] = tuple(spec.code for spec in _FIELDS)

# SPEC 6.7. Every field outside this allowlist has defaults disabled, and no
# continuous, count, text, tag or outcome field is ever in it (SPEC 6.5).
DEFAULT_ALLOWLIST_V1: Final[frozenset[FieldCode]] = frozenset(
    {
        FieldCode.FOOD_CHANGES,
        FieldCode.ACTIVITY_PARTICIPATION,
        FieldCode.SOCIAL_INTERACTIONS,
        FieldCode.EATING_STATUS,
        FieldCode.ATTENDANCE_STATUS,
    }
)

# SPEC 6.7. High signal fields that deliberately have no default.
HIGH_SIGNAL_NO_DEFAULT: Final[frozenset[FieldCode]] = frozenset(
    {
        FieldCode.SLEEP_QUALITY,
        FieldCode.WAKE_STATE,
        FieldCode.GI_STATUS,
        FieldCode.MEDICATION_ADHERENCE,
        FieldCode.ROUTINE_CHANGES,
        FieldCode.ALERTNESS,
        FieldCode.DAILY_REGULATION_STATE,
        FieldCode.DYSREGULATION_EVENT_COUNT,
        FieldCode.RELEVANT_EVENT_FLAG,
    }
)

# SPEC 6.10. Tuple order is the tie-break priority: lower index wins.
MONITORED_FIELDS: Final[tuple[FieldCode, ...]] = (
    FieldCode.SLEEP_QUALITY,
    FieldCode.WAKE_STATE,
    FieldCode.GI_STATUS,
    FieldCode.MEDICATION_ADHERENCE,
    FieldCode.DAILY_REGULATION_STATE,
)
MONITORED_FIELD_PRIORITY: Final[MappingProxyType[FieldCode, int]] = MappingProxyType(
    {code: index + 1 for index, code in enumerate(MONITORED_FIELDS)}
)

# SPEC 7.1. The same five fields, weighted equally, over a fixed 14-day window.
DQI_REQUIRED_FIELDS: Final[tuple[FieldCode, ...]] = MONITORED_FIELDS

# SPEC 9.7. The only fields `build_scenario` may read into a matching payload.
SCENARIO_ALLOWLIST_V1: Final[frozenset[FieldCode]] = frozenset(
    {
        FieldCode.SLEEP_QUALITY,
        FieldCode.ALERTNESS,
        FieldCode.GI_STATUS,
        FieldCode.MEDICATION_ADHERENCE,
        FieldCode.DAILY_REGULATION_STATE,
    }
)

# SPEC 6.5. No default is estimated for these kinds; defining bins or tolerances
# without validation would introduce an unjustified decision.
KINDS_WITHOUT_DEFAULTS: Final[frozenset[FieldKind]] = frozenset(
    {FieldKind.CONTINUOUS, FieldKind.COUNT, FieldKind.TEXT, FieldKind.TAG_SET}
)


FieldValue = bool | int | float | str | tuple[str, ...]


class UnknownFieldValueError(ValueError):
    """A value outside the field's declared support.

    Never coerced to `null`: an unmapped source value fails loudly so nobody
    silently turns a category the catalogue does not know into missingness
    (SPEC 5.3).
    """


def validate_field_value(code: FieldCode, value: object) -> FieldValue:
    """Check one observed value against its field, returning the canonical form."""

    spec = FIELD_CATALOG[code]
    kind = spec.kind

    if kind is FieldKind.BOOLEAN:
        if not isinstance(value, bool):
            raise UnknownFieldValueError(f"{code} expects a boolean")
        return value

    if kind in {FieldKind.COUNT, FieldKind.ORDINAL}:
        if isinstance(value, bool) or not isinstance(value, int):
            raise UnknownFieldValueError(f"{code} expects an integer")
        if spec.minimum is not None and value < spec.minimum:
            raise UnknownFieldValueError(f"{code} below its minimum")
        if spec.maximum is not None and value > spec.maximum:
            raise UnknownFieldValueError(f"{code} above its maximum")
        return value

    if kind is FieldKind.CONTINUOUS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnknownFieldValueError(f"{code} expects a number")
        number = float(value)
        if number != number:
            raise UnknownFieldValueError(f"{code} cannot be NaN")
        if spec.minimum is not None and number < spec.minimum:
            raise UnknownFieldValueError(f"{code} below its minimum")
        if spec.maximum is not None and number > spec.maximum:
            raise UnknownFieldValueError(f"{code} above its maximum")
        return number

    if kind is FieldKind.NOMINAL:
        allowed = spec.allowed_values() or ()
        if not isinstance(value, str) or value not in allowed:
            raise UnknownFieldValueError(f"{code} expects one of {allowed}")
        return value

    if kind is FieldKind.TAG_SET:
        if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set, frozenset)):
            raise UnknownFieldValueError(f"{code} expects a list of tags")
        tags = []
        for tag in value:
            if not isinstance(tag, str) or not TAG_PATTERN.match(tag):
                raise UnknownFieldValueError(f"{code} contains a tag outside the catalogue shape")
            tags.append(tag)
        return tuple(sorted(set(tags)))

    if not isinstance(value, str):
        raise UnknownFieldValueError(f"{code} expects text")
    if spec.max_length is not None and len(value) > spec.max_length:
        raise UnknownFieldValueError(f"{code} exceeds {spec.max_length} characters")
    return value


def field_spec(code: FieldCode) -> FieldSpec:
    return FIELD_CATALOG[code]


def applicable_fields(source: Source) -> tuple[FieldCode, ...]:
    """Fields the given source may report, in canonical catalogue order."""

    return tuple(code for code in CANONICAL_FIELD_ORDER if FIELD_CATALOG[code].allows(source))


def sources_for(code: FieldCode) -> tuple[Source, ...]:
    spec = FIELD_CATALOG[code]
    return tuple(source for source in Source if source in spec.allowed_sources)


def default_is_estimable(code: FieldCode) -> bool:
    """True only when the allowlist and the field kind both permit a suggestion."""

    spec = FIELD_CATALOG[code]
    return code in DEFAULT_ALLOWLIST_V1 and spec.kind not in KINDS_WITHOUT_DEFAULTS
