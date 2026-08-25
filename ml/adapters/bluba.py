"""Versioned mapping from the Bluba export vocabulary to canonical values.

This is the only place Bluba wording becomes a canonical value, so the mapping
stays auditable in one file (SPEC 5.3, CONVENTIONS 8.4).

What it will not do is the point. A category never becomes a count and never
becomes a position on a scale: `Estable con Apoyo` is not "1 episode",
`Presente` is not participation `4`, and `Reparador` is not a `5`. A category
the table does not know fails with `unmapped_source_value` instead of quietly
turning into `null`, because a value nobody mapped is not the same fact as a
value nobody reported (INV-35).

The export itself is untracked and its rights are undeclared
(`data/source-evidence.manifest.json`). This module can be read, tested and
reviewed without it.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from ml.errors import UnmappedSourceValueError
from packages.shared.enums import (
    Alertness,
    AttendanceStatus,
    DailyRegulationState,
    FieldCode,
    GiStatus,
    MedicationAdherence,
    SleepQuality,
    Source,
    WakeState,
)
from packages.shared.field_catalog import FieldValue, validate_field_value

MAPPING_VERSION = "bluba-mapping-0.3.0"

# Every distinct value the export actually contains is listed. The source
# vocabulary comes from `data/source-evidence.manifest.json`, which publishes
# closed categories precisely so an adapter can be written without the rows.
SLEEP_QUALITY_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Reparador": SleepQuality.RESTORATIVE.value,
        "Interrumpido": SleepQuality.INTERRUPTED.value,
        "Dificultad de Conciliación": SleepQuality.SLEEP_ONSET_DIFFICULTY.value,
    }
)
WAKE_STATE_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Tranquilo/Alegre": WakeState.CALM_HAPPY.value,
        "Cansado/Con Sueño": WakeState.TIRED_SLEEPY.value,
        "Irritable/Llorando": WakeState.IRRITABLE_CRYING.value,
    }
)
GI_STATUS_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Normal": GiStatus.NORMAL.value,
        "Estreñimiento": GiStatus.CONSTIPATION.value,
        "Diarrea": GiStatus.DIARRHEA.value,
    }
)
MEDICATION_ADHERENCE_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Sí": MedicationAdherence.TAKEN.value,
        "Si": MedicationAdherence.TAKEN.value,
        "No": MedicationAdherence.MISSED.value,
        "No Aplica": MedicationAdherence.NOT_APPLICABLE.value,
    }
)
DAILY_REGULATION_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Excelente": DailyRegulationState.EXCELLENT.value,
        "Estable con Apoyo": DailyRegulationState.STABLE_WITH_SUPPORT.value,
        "Desregulación Frecuente": DailyRegulationState.FREQUENT_DYSREGULATION.value,
    }
)
ALERTNESS_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Bajo (Letárgico)": Alertness.LOW.value,
        "Calmado": Alertness.CALM.value,
        "Óptimo (Regulado)": Alertness.OPTIMAL.value,
        "Alto (Sobreexcitado)": Alertness.HIGH.value,
    }
)
ATTENDANCE_MAP: MappingProxyType[str, str] = MappingProxyType(
    {
        "Presente": AttendanceStatus.PRESENT.value,
        "Ausente": AttendanceStatus.ABSENT.value,
    }
)

FIELD_MAPS: MappingProxyType[FieldCode, MappingProxyType[str, str]] = MappingProxyType(
    {
        FieldCode.SLEEP_QUALITY: SLEEP_QUALITY_MAP,
        FieldCode.WAKE_STATE: WAKE_STATE_MAP,
        FieldCode.GI_STATUS: GI_STATUS_MAP,
        FieldCode.MEDICATION_ADHERENCE: MEDICATION_ADHERENCE_MAP,
        FieldCode.DAILY_REGULATION_STATE: DAILY_REGULATION_MAP,
        FieldCode.ALERTNESS: ALERTNESS_MAP,
        FieldCode.ATTENDANCE_STATUS: ATTENDANCE_MAP,
    }
)

# SPEC 4.3: the export grades intensity in three bands. That proves the category
# exists; it does not define a target and it is not a label on its own. The
# adapter therefore exposes the band, and a versioned `TargetDefinitionVersion`
# decides what, if anything, it means.
INTENSITY_BANDS = ("Leve (1-3)", "Moderada (4-7)", "Severa (8-10)")
SEVERE_INTENSITY_BAND = "Severa (8-10)"


@dataclass(frozen=True, slots=True)
class MappedValue:
    """A canonical value together with the raw text it came from."""

    field_code: FieldCode
    value: FieldValue
    raw_value: str
    mapping_version: str = MAPPING_VERSION


def map_value(field_code: FieldCode, raw_value: str) -> MappedValue:
    """Translate one export cell, or fail loudly.

    An empty cell is not a category either: the caller decides whether an absent
    cell means "not reported", and neither answer is invented here.
    """

    table = FIELD_MAPS.get(field_code)
    if table is None:
        raise UnmappedSourceValueError(f"{field_code} has no Bluba mapping")
    text = raw_value.strip()
    if not text:
        raise UnmappedSourceValueError(f"{field_code} received an empty source value")
    canonical = table.get(text)
    if canonical is None:
        raise UnmappedSourceValueError(
            f"{field_code} has no mapping for the source value {text!r} in {MAPPING_VERSION}"
        )
    return MappedValue(
        field_code=field_code,
        value=validate_field_value(field_code, canonical),
        raw_value=text,
    )


def mapped_fields_for(source: Source) -> tuple[FieldCode, ...]:
    """Which mapped fields the given observation context may report."""

    from packages.shared.field_catalog import FIELD_CATALOG

    return tuple(
        field_code for field_code in FIELD_MAPS if FIELD_CATALOG[field_code].allows(source)
    )


def source_vocabulary(field_code: FieldCode) -> tuple[str, ...]:
    """The export wording this mapping version accepts for one field."""

    table = FIELD_MAPS.get(field_code)
    if table is None:
        raise UnmappedSourceValueError(f"{field_code} has no Bluba mapping")
    return tuple(sorted(table))
