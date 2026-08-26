"""Lectura de los cinco CSV del desafío.

Sólo lee y valida forma: la traducción de valores vive en `mapping.py` y la
escritura en `importer.py`. Los CSV vienen con BOM y separador `;`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

DELIMITER = ";"
ENCODING = "utf-8-sig"

CASES_FILE = "1_casos_anonimizados.csv"
GOALS_FILE = "2_programas_y_objetivos.csv"
SESSIONS_FILE = "3_sesiones_profesionales.csv"
DAILY_FILE = "4_seguimiento_diario_tutor.csv"
EVENTS_FILE = "5_eventos_desregulacion_tutor.csv"


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    age_range: str
    diagnosis: str
    sensory_profile: str


@dataclass(frozen=True, slots=True)
class DailyRecord:
    record_id: str
    case_id: str
    day: date
    sleep_quality: str
    wake_state: str
    medication_adherence: str
    gi_status: str
    daily_regulation_state: str


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    case_id: str
    day: date
    profession: str
    attendance: str
    alertness_initial: str
    alertness_final: str


@dataclass(frozen=True, slots=True)
class DysregulationEvent:
    event_id: str
    case_id: str
    occurred_at: datetime
    kind: str
    intensity: str
    trigger: str
    strategy: str
    outcome: str


@dataclass(frozen=True, slots=True)
class Dataset:
    cases: tuple[Case, ...]
    daily: tuple[DailyRecord, ...]
    sessions: tuple[Session, ...]
    events: tuple[DysregulationEvent, ...]

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(case.case_id for case in self.cases)


def _rows(directory: Path, name: str) -> list[dict[str, str]]:
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"falta {name} en {directory}")
    with path.open(encoding=ENCODING, newline="") as handle:
        return list(csv.DictReader(handle, delimiter=DELIMITER))


def load_dataset(directory: Path) -> Dataset:
    """Lee los cinco archivos y comprueba la integridad referencial por caso."""

    cases = tuple(
        Case(
            case_id=row["id_caso"].strip(),
            age_range=row["rango_edad"].strip(),
            diagnosis=row["diagnostico_principal"].strip(),
            sensory_profile=row["perfil_sensorial_predominante"].strip(),
        )
        for row in _rows(directory, CASES_FILE)
    )
    known = {case.case_id for case in cases}

    daily = tuple(
        DailyRecord(
            record_id=row["id_registro_diario"].strip(),
            case_id=row["id_caso"].strip(),
            day=date.fromisoformat(row["fecha"].strip()),
            sleep_quality=row["calidad_sueno"].strip(),
            wake_state=row["modo_despertar"].strip(),
            medication_adherence=row["adherencia_medicacion"].strip(),
            gi_status=row["estado_gastrointestinal"].strip(),
            daily_regulation_state=row["nivel_regulacion_general_dia"].strip(),
        )
        for row in _rows(directory, DAILY_FILE)
    )

    sessions = tuple(
        Session(
            session_id=row["id_sesion"].strip(),
            case_id=row["id_caso"].strip(),
            day=date.fromisoformat(row["fecha_sesion"].strip()),
            profession=row["profesion"].strip(),
            attendance=row["estado_asistencia"].strip(),
            alertness_initial=row["nivel_alerta_inicial"].strip(),
            alertness_final=row["nivel_alerta_final"].strip(),
        )
        for row in _rows(directory, SESSIONS_FILE)
    )

    events = tuple(
        DysregulationEvent(
            event_id=row["id_evento"].strip(),
            case_id=row["id_caso"].strip(),
            occurred_at=datetime.strptime(row["fecha_hora"].strip(), "%Y-%m-%d %H:%M"),
            kind=row["tipo_evento"].strip(),
            intensity=row["intensidad"].strip(),
            trigger=row["detonante_gatillante"].strip(),
            strategy=row["estrategia_calma_aplicada"].strip(),
            outcome=row["resultado_estrategia"].strip(),
        )
        for row in _rows(directory, EVENTS_FILE)
    )

    for label, rows in (("diario", daily), ("sesiones", sessions), ("eventos", events)):
        unknown = {row.case_id for row in rows} - known
        if unknown:
            raise ValueError(f"{label}: casos sin ficha en {CASES_FILE}: {sorted(unknown)}")

    duplicates = _duplicate_days(daily)
    if duplicates:
        raise ValueError(f"registro diario duplicado para {duplicates}")

    return Dataset(cases=cases, daily=daily, sessions=sessions, events=events)


def _duplicate_days(daily: tuple[DailyRecord, ...]) -> list[tuple[str, str]]:
    """Un caso con dos registros el mismo día rompe un episodio por día."""

    seen: set[tuple[str, date]] = set()
    duplicates: list[tuple[str, str]] = []
    for record in daily:
        key = (record.case_id, record.day)
        if key in seen:
            duplicates.append((record.case_id, record.day.isoformat()))
        seen.add(key)
    return duplicates
