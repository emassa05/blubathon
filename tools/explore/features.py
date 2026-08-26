"""Matriz `(sujeto, día) → variables del día + desenlace de las 24 h siguientes`.

La alineación temporal es lo único delicado acá. El episodio del día D se abre
a las 20:00 hora de Santiago, que en invierno son las 00:00 UTC del día D+1; su
`local_date` es D y su ventana objetivo es [D 20:00, D+1 20:00). La observación
que corresponde es la del día local D, la que el tutor cerró al abrir el
episodio — nunca la del día siguiente, que ya cae dentro de la ventana que
estamos prediciendo.

Comparar con `date(as_of_at)` en UTC da D+1 y mete dentro del predictor un
registro posterior al corte. El repositorio tiene `local_date` justamente para
que eso no pase.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date

from apps.api.canonical import parse_timestamp
from apps.api.services.local_time import local_date
from packages.shared.field_catalog import FieldCode

# Variables del registro diario del tutor más el nivel de alerta que reporta la
# terapia. Se excluyen `notes` y `behavior_tags`: son texto libre, y el objetivo
# de este análisis es ordenar variables estructuradas.
CANDIDATE_FIELDS: tuple[FieldCode, ...] = (
    FieldCode.SLEEP_QUALITY,
    FieldCode.WAKE_STATE,
    FieldCode.MEDICATION_ADHERENCE,
    FieldCode.GI_STATUS,
    FieldCode.DAILY_REGULATION_STATE,
    FieldCode.ALERTNESS,
)


@dataclass(frozen=True, slots=True)
class FeatureMatrix:
    """Filas alineadas, con los nombres de columna que el reporte va a citar."""

    columns: tuple[str, ...]
    rows: tuple[tuple[str | None, ...], ...]
    labels: tuple[int, ...]
    subjects: tuple[str, ...]
    days: tuple[date, ...]
    dropped_incomplete: int
    dropped_columns: tuple[tuple[str, float], ...] = ()
    constant_columns: tuple[str, ...] = ()

    @property
    def positives(self) -> int:
        return sum(self.labels)

    @property
    def negatives(self) -> int:
        return len(self.labels) - self.positives

    @property
    def prevalence(self) -> float:
        return self.positives / len(self.labels) if self.labels else 0.0


def build_matrix(connection: sqlite3.Connection, *, min_coverage: float = 0.9) -> FeatureMatrix:
    """Una fila por episodio primario resuelto, con las variables de su día local.

    Una variable que sólo se registra algunos días no se puede exigir junto a
    las diarias: `alertness` viene de la sesión de terapia y existe en 37 de 102
    días, así que pedirla completa restringe el análisis a los días con terapia
    —un tercio de la muestra y otra población— sin decirlo. Las columnas por
    debajo de `min_coverage` se descartan enteras y el reporte las nombra; sólo
    después se descartan las filas incompletas que queden.
    """

    connection.row_factory = sqlite3.Row

    observed: dict[tuple[str, date, str], str] = {}
    for row in connection.execute(
        "SELECT subject_id, local_date, field_code, value FROM field_observations"
        " WHERE value IS NOT NULL"
    ):
        key = (row["subject_id"], date.fromisoformat(row["local_date"]), row["field_code"])
        observed[key] = json.loads(row["value"])

    episodes = [
        (row["subject_id"], local_date(parse_timestamp(row["as_of_at"])), row["status"])
        for row in connection.execute(
            "SELECT e.subject_id, e.as_of_at, r.status"
            " FROM prediction_episodes AS e"
            " JOIN outcome_resolutions AS r"
            "   ON r.prediction_episode_id = e.prediction_episode_id"
            " WHERE e.role = 'primary' AND r.status IN ('yes', 'no')"
            " ORDER BY e.subject_id, e.as_of_at"
        )
    ]

    candidates = tuple(field.value for field in CANDIDATE_FIELDS)
    coverage = {
        name: (
            sum(1 for subject_id, day, _ in episodes if (subject_id, day, name) in observed)
            / len(episodes)
            if episodes
            else 0.0
        )
        for name in candidates
    }
    covered = tuple(name for name in candidates if coverage[name] >= min_coverage)
    sparse = tuple((name, coverage[name]) for name in candidates if coverage[name] < min_coverage)

    columns = tuple(name for name in covered if _varies_within_subject(episodes, observed, name))
    constant = tuple(name for name in covered if name not in columns)

    rows: list[tuple[str | None, ...]] = []
    labels: list[int] = []
    subjects: list[str] = []
    days: list[date] = []
    dropped = 0

    for subject_id, day, status in episodes:
        values = tuple(observed.get((subject_id, day, name)) for name in columns)
        if any(value is None for value in values):
            dropped += 1
            continue
        rows.append(values)
        labels.append(1 if status == "yes" else 0)
        subjects.append(subject_id)
        days.append(day)

    return FeatureMatrix(
        columns=columns,
        rows=tuple(rows),
        labels=tuple(labels),
        subjects=tuple(subjects),
        days=tuple(days),
        dropped_incomplete=dropped,
        dropped_columns=sparse,
        constant_columns=constant,
    )


def _varies_within_subject(
    episodes: list[tuple[str, date, str]],
    observed: dict[tuple[str, date, str], str],
    name: str,
) -> bool:
    """¿La variable cambia de un día a otro dentro de algún sujeto?

    Una que no cambia nunca dentro del sujeto es un atributo de la persona, no
    una observación diaria, y no puede explicar por qué un día terminó en crisis
    y el siguiente no. Peor: al medir importancia por permutación dejando un
    sujeto afuera, barajarla dentro de ese sujeto no altera nada, su importancia
    da exactamente cero, y cero le gana a las variables reales cuando todas
    salen negativas. Ganaría el ranking por no hacer nada.
    """

    by_subject: dict[str, set[str]] = {}
    for subject_id, day, _ in episodes:
        value = observed.get((subject_id, day, name))
        if value is not None:
            by_subject.setdefault(subject_id, set()).add(value)
    return any(len(values) > 1 for values in by_subject.values())
