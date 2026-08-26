"""Tablas de traducción CSV → catálogo de campos.

Cada tabla es total sobre los valores que aparecen en el conjunto entregado.
`translate` levanta `UnmappedValueError` ante cualquier otro: preferimos que la
importación se detenga a que un valor desconocido entre como `other` y quede
indistinguible de una categoría legítima.
"""

from __future__ import annotations

from types import MappingProxyType

from packages.shared.field_catalog import (
    Alertness,
    DailyRegulationState,
    FieldCode,
    GiStatus,
    MedicationAdherence,
    SleepQuality,
    WakeState,
)


class UnmappedValueError(ValueError):
    """Un valor del CSV no está en la tabla de traducción."""


# 4_seguimiento_diario_tutor.csv
SLEEP_QUALITY: MappingProxyType[str, str] = MappingProxyType(
    {
        "Reparador": SleepQuality.RESTORATIVE.value,
        "Interrumpido": SleepQuality.INTERRUPTED.value,
        "Dificultad de Conciliación": SleepQuality.SLEEP_ONSET_DIFFICULTY.value,
    }
)

WAKE_STATE: MappingProxyType[str, str] = MappingProxyType(
    {
        "Tranquilo/Alegre": WakeState.CALM_HAPPY.value,
        "Cansado/Con Sueño": WakeState.TIRED_SLEEPY.value,
        "Irritable/Llorando": WakeState.IRRITABLE_CRYING.value,
    }
)

MEDICATION_ADHERENCE: MappingProxyType[str, str] = MappingProxyType(
    {
        "Sí": MedicationAdherence.TAKEN.value,
        "No": MedicationAdherence.MISSED.value,
        "No Aplica": MedicationAdherence.NOT_APPLICABLE.value,
    }
)

GI_STATUS: MappingProxyType[str, str] = MappingProxyType(
    {
        "Normal": GiStatus.NORMAL.value,
        "Estreñimiento": GiStatus.CONSTIPATION.value,
        "Diarrea": GiStatus.DIARRHEA.value,
    }
)

DAILY_REGULATION_STATE: MappingProxyType[str, str] = MappingProxyType(
    {
        "Excelente": DailyRegulationState.EXCELLENT.value,
        "Estable con Apoyo": DailyRegulationState.STABLE_WITH_SUPPORT.value,
        "Desregulación Frecuente": DailyRegulationState.FREQUENT_DYSREGULATION.value,
    }
)

# 3_sesiones_profesionales.csv. `Calmado` sólo aparece como nivel final: es el
# estado al que la sesión llevó al niño, y el catálogo ya lo distingue de
# `optimal`, así que no se colapsan.
ALERTNESS: MappingProxyType[str, str] = MappingProxyType(
    {
        "Óptimo (Regulado)": Alertness.OPTIMAL.value,
        "Alto (Sobreexcitado)": Alertness.HIGH.value,
        "Bajo (Letárgico)": Alertness.LOW.value,
        "Calmado": Alertness.CALM.value,
    }
)

# Columna del CSV diario → campo del catálogo y tabla que lo traduce.
DAILY_COLUMNS: tuple[tuple[str, FieldCode, MappingProxyType[str, str]], ...] = (
    ("calidad_sueno", FieldCode.SLEEP_QUALITY, SLEEP_QUALITY),
    ("modo_despertar", FieldCode.WAKE_STATE, WAKE_STATE),
    ("adherencia_medicacion", FieldCode.MEDICATION_ADHERENCE, MEDICATION_ADHERENCE),
    ("estado_gastrointestinal", FieldCode.GI_STATUS, GI_STATUS),
    ("nivel_regulacion_general_dia", FieldCode.DAILY_REGULATION_STATE, DAILY_REGULATION_STATE),
)


def translate(table: MappingProxyType[str, str], raw: str, *, column: str) -> str:
    """Traduce un valor del CSV, o falla nombrando la columna y el valor."""

    try:
        return table[raw.strip()]
    except KeyError:
        raise UnmappedValueError(
            f"{column}: valor {raw.strip()!r} sin traducción; conocidos: {sorted(table)}"
        ) from None
