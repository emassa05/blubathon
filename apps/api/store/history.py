"""Lecturas de historial que el dominio puro de P1 necesita como entrada.

Todo el SQL del proyecto vive bajo `apps/api/store`, así que
los adaptadores de `apps/api/adapters/p1` piden aquí las filas y traducen ellos
a los modelos de `packages/shared`.

Este módulo solo lee. No calcula ventanas, promedios ni estados derivados: eso
es dominio y `store-does-not-compute` lo verifica.
"""

from __future__ import annotations

import sqlite3

TRACK_PREFERENCE = (
    "real_logit_challenger_v1",
    "real_personal_baseline_v1",
)

#: Elige la primera salida expuesta con probabilidad, en el orden de arriba.
OPERATIONAL_OUTPUT_SQL = """
    SELECT * FROM prediction_outputs AS o
     WHERE o.prediction_episode_id = :episode
       AND o.exposed = 1
     ORDER BY (o.probability IS NULL),
              CASE o.track_id
                WHEN 'real_logit_challenger_v1' THEN 0
                WHEN 'real_personal_baseline_v1' THEN 1
                ELSE 2 END
     LIMIT 1
"""


def operational_output(
    connection: sqlite3.Connection, prediction_episode_id: str
) -> sqlite3.Row | None:
    """La salida cuyo número ve el usuario, abstenida o no."""
    return connection.execute(OPERATIONAL_OUTPUT_SQL, {"episode": prediction_episode_id}).fetchone()


def observations_for_subject(
    connection: sqlite3.Connection, *, tenant_id: str, subject_id: str, since_local_date: str
) -> list[sqlite3.Row]:
    """Observaciones del sujeto desde una fecha local, en orden de ingesta."""
    return list(
        connection.execute(
            "SELECT * FROM field_observations"
            " WHERE tenant_id = ? AND subject_id = ? AND local_date >= ?"
            " ORDER BY ingested_at, field_observation_id",
            (tenant_id, subject_id, since_local_date),
        ).fetchall()
    )


def observations_for_session(
    connection: sqlite3.Connection, *, form_session_id: str
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT * FROM field_observations WHERE form_session_id = ?"
            " ORDER BY ingested_at, field_observation_id",
            (form_session_id,),
        ).fetchall()
    )


def presentations_for_subject(
    connection: sqlite3.Connection, *, tenant_id: str, subject_id: str
) -> list[sqlite3.Row]:
    """Presentaciones de preguntas, que fijan el reloj de antigüedad."""
    return list(
        connection.execute(
            "SELECT * FROM question_presentations WHERE tenant_id = ? AND subject_id = ?"
            " ORDER BY presented_at, question_presentation_id",
            (tenant_id, subject_id),
        ).fetchall()
    )


def approved_mapping_ids(connection: sqlite3.Connection, *, tenant_id: str) -> tuple[str, ...]:
    """Una fila importada solo cuenta con mapping aprobado."""
    rows = connection.execute(
        "SELECT source_mapping_id FROM source_mappings"
        " WHERE tenant_id = ? AND approval_status = 'approved'",
        (tenant_id,),
    ).fetchall()
    return tuple(str(row["source_mapping_id"]) for row in rows)


def subject_profile_rows(
    connection: sqlite3.Connection, *, tenant_id: str, subject_id: str, cutoff: str
) -> list[sqlite3.Row]:
    """Filas completas del perfil vigentes al cutoff, sin proyectar."""
    return list(
        connection.execute(
            "SELECT * FROM subject_profiles WHERE tenant_id = ? AND subject_id = ?"
            " AND effective_from <= ? ORDER BY effective_from, subject_profile_id",
            (tenant_id, subject_id, cutoff),
        ).fetchall()
    )


def previous_primary_episodes(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    before_at: str,
) -> list[sqlite3.Row]:
    """Episodios primarios anteriores del sujeto con su resolución activa.

    La resolución activa es la hoja de la cadena `supersedes_id`; se devuelven
    todas las filas y el adaptador proyecta al cutoff.

    `cohort_kind` y `feature_snapshot_id` no viven en `prediction_episodes`,
    pero el episodio del dominio los declara: se unen aquí para que
    `rows.prediction_episode` pueda traducir la fila. Un `SELECT *` a secas
    traduce bien mientras el sujeto no tenga episodios previos y revienta con
    `IndexError` en cuanto tiene uno, que es justo cuando el baseline empieza a
    servir para algo.
    """
    return list(
        connection.execute(
            "SELECT episode.*, subject.cohort_kind AS cohort_kind,"
            " snapshot.feature_snapshot_id AS feature_snapshot_id"
            " FROM prediction_episodes AS episode"
            " JOIN subjects AS subject ON subject.subject_id = episode.subject_id"
            " LEFT JOIN feature_snapshots AS snapshot"
            "   ON snapshot.prediction_episode_id = episode.prediction_episode_id"
            " WHERE episode.tenant_id = ? AND episode.subject_id = ?"
            " AND episode.role = 'primary' AND episode.target_end_at <= ?"
            " ORDER BY episode.target_start_at, episode.prediction_episode_id",
            (tenant_id, subject_id, before_at),
        ).fetchall()
    )


def resolutions_for_episodes(
    connection: sqlite3.Connection, *, prediction_episode_ids: tuple[str, ...]
) -> list[sqlite3.Row]:
    if not prediction_episode_ids:
        return []
    placeholders = ",".join("?" for _ in prediction_episode_ids)
    return list(
        connection.execute(
            f"SELECT * FROM outcome_resolutions WHERE prediction_episode_id IN ({placeholders})"
            " ORDER BY ingested_at, outcome_resolution_id",
            prediction_episode_ids,
        ).fetchall()
    )


def shadow_model_version(
    connection: sqlite3.Connection, *, tenant_id: str, track_id: str
) -> sqlite3.Row | None:
    """Versión en estado `shadow` de un track, si `tools/train` publicó alguna."""
    return connection.execute(
        "SELECT * FROM model_versions WHERE tenant_id = ? AND track_id = ? AND state = 'shadow'"
        " ORDER BY state_changed_at DESC LIMIT 1",
        (tenant_id, track_id),
    ).fetchone()


def child_submission_days(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    limit: int,
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT f.local_date, f.form_session_id AS submission_id,"
            " e.prediction_episode_id, p.status AS prediction_status, p.probability,"
            " p.interval_low, p.interval_high, i.recommendation_instance_id,"
            " i.status AS recommendation_status, r.status AS outcome_status,"
            " r.resolved_at AS outcome_reported_at"
            " FROM form_sessions AS f"
            " LEFT JOIN prediction_episodes AS e ON e.form_session_id = f.form_session_id"
            # El track ya no se fija a mano: gana el challenger si estimó, y
            # si no la tasa base. `p.status` sale del que de verdad se muestra.
            # El track ya no se fija a mano. Primero cualquiera que haya
            # estimado, y entre esos el challenger, que corrige la tasa base con
            # el día declarado. Si ninguno estimó se toma igual una fila: la
            # abstención tiene que llegar a la pantalla como abstención, no como
            # un día sin predicción.
            " LEFT JOIN prediction_outputs AS p"
            "  ON p.prediction_output_id = ("
            "     SELECT o.prediction_output_id FROM prediction_outputs AS o"
            "      WHERE o.prediction_episode_id = e.prediction_episode_id"
            "        AND o.exposed = 1"
            "      ORDER BY (o.probability IS NULL),"
            "               CASE o.track_id"
            "                 WHEN 'real_logit_challenger_v1' THEN 0"
            "                 WHEN 'real_personal_baseline_v1' THEN 1"
            "                 ELSE 2 END"
            "      LIMIT 1)"
            " LEFT JOIN recommendation_instances AS i"
            "  ON i.prediction_episode_id = e.prediction_episode_id"
            " LEFT JOIN outcome_resolutions AS r"
            "  ON r.prediction_episode_id = e.prediction_episode_id"
            "  AND NOT EXISTS (SELECT 1 FROM outcome_resolutions AS newer"
            "                  WHERE newer.supersedes_id = r.outcome_resolution_id)"
            " WHERE f.tenant_id = ? AND f.subject_id = ? AND f.status = 'submitted'"
            " ORDER BY f.local_date DESC, f.submitted_at DESC LIMIT ?",
            (tenant_id, subject_id, limit),
        ).fetchall()
    )


def resolved_predictions(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
) -> list[sqlite3.Row]:
    """Lo que se anunció y lo que ocurrió, de toda la cohorte de la organización.

    Un par por episodio resuelto: la probabilidad que se **enseñó** ese día y si
    hubo episodio. Nada más, porque es lo único que la calibración necesita y
    porque cualquier otra columna invitaría a cruzarla con la persona, que es
    justo lo que esta medida no hace.

    El track se elige igual que en `child_submission_days`, y tiene que seguir
    siendo igual: si se calibrara sobre un track distinto del que se ve, estaría
    midiendo un número que nadie llegó a leer. Por eso `exposed = 1` y el mismo
    orden de preferencia.

    Solo entran los desenlaces vigentes —los que nadie ha superado con uno
    posterior— y solo `yes` y `no`: un `unknown` o un conflicto no dicen si
    ocurrió, y contarlos como "no" convertiría una duda en un acierto.
    """

    return list(
        connection.execute(
            "SELECT p.probability, r.status AS outcome_status"
            " FROM prediction_episodes AS e"
            " JOIN prediction_outputs AS p"
            "  ON p.prediction_output_id = ("
            "     SELECT o.prediction_output_id FROM prediction_outputs AS o"
            "      WHERE o.prediction_episode_id = e.prediction_episode_id"
            "        AND o.exposed = 1"
            "        AND o.status = 'ok'"
            "        AND o.probability IS NOT NULL"
            "      ORDER BY CASE o.track_id"
            "                 WHEN 'real_logit_challenger_v1' THEN 0"
            "                 WHEN 'real_personal_baseline_v1' THEN 1"
            "                 ELSE 2 END"
            "      LIMIT 1)"
            " JOIN outcome_resolutions AS r"
            "  ON r.prediction_episode_id = e.prediction_episode_id"
            "  AND NOT EXISTS (SELECT 1 FROM outcome_resolutions AS newer"
            "                  WHERE newer.supersedes_id = r.outcome_resolution_id)"
            " WHERE e.tenant_id = ? AND r.status IN ('yes', 'no')"
            " ORDER BY e.as_of_at",
            (tenant_id,),
        ).fetchall()
    )
