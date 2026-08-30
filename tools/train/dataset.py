"""Arma el conjunto de entrenamiento y anota exactamente de qué filas salió.

El challenger predice sobre la desviación del día respecto de la costumbre del
niño: no «durmió mal» sino «durmió peor que sus últimos 30 días». Eso obliga a
reconstruir, para cada episodio, el estado de la base **en el instante en que
ese episodio se abrió** —nunca el estado de hoy—, que es de donde salen los dos
predictores y la tasa base personal.

De ahí que esto no sea un `SELECT` y ya: recorre los episodios de cada niño en
orden y va acumulando su historia, igual que la habría visto el sistema en vivo.
Un episodio con menos de `BASELINE_MIN_OUTCOMES` desenlaces previos no entra,
porque en vivo tampoco habría tenido tasa base.

Junto con las filas se guardan los identificadores de todo lo que se leyó. Esos
identificadores son el snapshot: fijan a qué datos se refiere el Brier que se
reporte después, de modo que el número no quede flotando sobre «la base», que
cambia cada vez que un tutor registra un día.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import parse_timestamp
from apps.api.store import history
from ml.prediction.baseline import BASELINE_MIN_OUTCOMES, DEFAULT_PRIOR_PER_CATEGORY
from ml.prediction.challenger import (
    CHALLENGER_PREDICTOR_FIELDS,
    ChallengerRow,
    predictor_deviations,
)
from packages.shared.enums import FieldCode, Source

# Los dos predictores del challenger. Están fijados desde antes de mirar los
# datos y por eso el Brier fuera de muestra es honesto; agregar una variable acá
# porque la tabla de frecuencias la premió convertiría la evaluación en un
# ejercicio circular.
# La lista vive en `ml.prediction.challenger`: entrenar y puntuar tienen que
# mirar exactamente los mismos predictores.
PREDICTORS: tuple[FieldCode, ...] = CHALLENGER_PREDICTOR_FIELDS

VERIFIED_STATUSES = ("yes", "no")


@dataclass(frozen=True, slots=True)
class TrainingDataset:
    """Las filas del entrenamiento y la huella de los datos que las produjeron."""

    rows: tuple[ChallengerRow, ...]
    episode_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    outcome_ids: tuple[str, ...]
    consent_ids: tuple[str, ...]
    subject_ids: tuple[str, ...]
    cutoff_at: datetime
    skipped_without_baseline: int
    skipped_without_predictors: int

    @property
    def n_positive(self) -> int:
        return sum(row.label for row in self.rows)

    @property
    def n_negative(self) -> int:
        return len(self.rows) - self.n_positive

    @property
    def content_sha256(self) -> str:
        """Huella de los identificadores, no de los valores.

        Si mañana se corrige el valor de una observación ya registrada, los
        identificadores no cambian y el hash tampoco: dos evaluaciones sobre
        datos distintos podrían compartir huella. Se acepta porque el esquema
        trata la corrección como una fila nueva —`ingested_at` posterior— y no
        como una edición en el lugar.
        """

        payload = json.dumps(
            {
                "episodes": sorted(self.episode_ids),
                "observations": sorted(self.observation_ids),
                "outcomes": sorted(self.outcome_ids),
                "subjects": sorted(self.subject_ids),
            },
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_dataset(
    connection: sqlite3.Connection, *, tenant_id: str, cutoff_at: datetime
) -> TrainingDataset:
    """Una fila por episodio resuelto que en vivo habría tenido tasa base."""

    connection.row_factory = sqlite3.Row
    subjects = connection.execute(
        "SELECT subject_id FROM subjects WHERE tenant_id = ? AND cohort_kind = 'real_subject'"
        " ORDER BY subject_id",
        (tenant_id,),
    ).fetchall()

    rows: list[ChallengerRow] = []
    episode_ids: list[str] = []
    observation_ids: list[str] = []
    outcome_ids: list[str] = []
    subject_ids: list[str] = []
    without_baseline = 0
    without_predictors = 0

    for subject in subjects:
        subject_id = subject["subject_id"]
        observation_rows = history.observations_for_subject(
            connection, tenant_id=tenant_id, subject_id=subject_id, since_local_date="0001-01-01"
        )
        observations = [translate.field_observation(row) for row in observation_rows]
        episodes = connection.execute(
            "SELECT e.prediction_episode_id, e.as_of_at,"
            " r.outcome_resolution_id, r.status"
            " FROM prediction_episodes AS e"
            " JOIN outcome_resolutions AS r"
            "   ON r.prediction_episode_id = e.prediction_episode_id"
            " WHERE e.tenant_id = ? AND e.subject_id = ? AND e.role = 'primary'"
            f" AND r.status IN ({','.join('?' * len(VERIFIED_STATUSES))})"
            " AND e.as_of_at <= ?"
            " ORDER BY e.as_of_at",
            (tenant_id, subject_id, *VERIFIED_STATUSES, cutoff_at.isoformat()),
        ).fetchall()
        if not episodes:
            continue

        subject_ids.append(subject_id)
        observation_ids.extend(str(row["field_observation_id"]) for row in observation_rows)

        seen_labels: list[int] = []
        for episode in episodes:
            label = 1 if episode["status"] == "yes" else 0
            as_of = parse_timestamp(episode["as_of_at"])

            # La tasa base que el baseline habría publicado ese día, con los
            # desenlaces que ya estaban resueltos y no uno más.
            if len(seen_labels) < BASELINE_MIN_OUTCOMES:
                without_baseline += 1
                seen_labels.append(label)
                continue
            p_base = (DEFAULT_PRIOR_PER_CATEGORY + sum(seen_labels)) / (
                2 * DEFAULT_PRIOR_PER_CATEGORY + len(seen_labels)
            )

            deviations = _deviations(
                observations,
                tenant_id=tenant_id,
                subject_id=subject_id,
                as_of=as_of,
            )
            seen_labels.append(label)
            # El entrenamiento sigue exigiendo los dos predictores observados, y
            # no se conforma con la desviación cero que el runtime sí acepta.
            #
            # La definición de la feature es la misma —la de `predictor_deviations`,
            # que es justo lo que no puede diferir—; lo que difiere es a qué filas
            # se entrena, que es otra decisión y siempre lo fue. Un cero imputado
            # es "no sé qué pasó ese día", y entrenar con eso mete filas sin señal
            # que solo encogen los coeficientes. Puntuar con él es distinto: ahí no
            # se elige la fila, la fila es el día que hay, y un cero cae de lleno
            # dentro de lo que el modelo vio, porque los días en la costumbre
            # también dan cero.
            if deviations.costumbre_desconocida or not deviations.todos_observados:
                without_predictors += 1
                continue

            rows.append(
                ChallengerRow(
                    subject_id=UUID(subject_id),
                    p_base=p_base,
                    sleep_deviation=deviations.valores[FieldCode.SLEEP_QUALITY],
                    regulation_deviation=deviations.valores[FieldCode.DAILY_REGULATION_STATE],
                    label=label,
                )
            )
            episode_ids.append(str(episode["prediction_episode_id"]))
            outcome_ids.append(str(episode["outcome_resolution_id"]))

    consent_ids = [
        str(row["consent_id"])
        for row in connection.execute(
            "SELECT consent_id FROM consents WHERE tenant_id = ? ORDER BY consent_id",
            (tenant_id,),
        )
    ]

    return TrainingDataset(
        rows=tuple(rows),
        episode_ids=tuple(episode_ids),
        observation_ids=tuple(observation_ids),
        outcome_ids=tuple(outcome_ids),
        consent_ids=tuple(consent_ids),
        subject_ids=tuple(subject_ids),
        cutoff_at=cutoff_at,
        skipped_without_baseline=without_baseline,
        skipped_without_predictors=without_predictors,
    )


def _deviations(
    observations: list,
    *,
    tenant_id: str,
    subject_id: str,
    as_of: datetime,
) -> dict[FieldCode, float | None]:
    """Delega en la definición compartida con el runtime."""

    return predictor_deviations(
        observations,
        tenant_id=UUID(tenant_id),
        subject_id=UUID(subject_id),
        source=Source.HOME,
        as_of_at=as_of,
    )
