"""Lecturas de historial que el dominio puro de P1 necesita como entrada.

Todo el SQL del proyecto vive bajo `apps/api/store` (CONVENTIONS 12.1), así que
los adaptadores de `apps/api/adapters/p1` piden aquí las filas y traducen ellos
a los modelos de `packages/shared`.

Este módulo solo lee. No calcula ventanas, promedios ni estados derivados: eso
es dominio y `store-does-not-compute` lo verifica.
"""

from __future__ import annotations

import sqlite3


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
    """Presentaciones de preguntas, que fijan el reloj de antigüedad (SPEC 6.10)."""
    return list(
        connection.execute(
            "SELECT * FROM question_presentations WHERE tenant_id = ? AND subject_id = ?"
            " ORDER BY presented_at, question_presentation_id",
            (tenant_id, subject_id),
        ).fetchall()
    )


def approved_mapping_ids(connection: sqlite3.Connection, *, tenant_id: str) -> tuple[str, ...]:
    """SPEC 6.2: una fila importada solo cuenta con mapping aprobado."""
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
    """
    return list(
        connection.execute(
            "SELECT * FROM prediction_episodes"
            " WHERE tenant_id = ? AND subject_id = ? AND role = 'primary'"
            " AND target_end_at <= ?"
            " ORDER BY target_start_at, prediction_episode_id",
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


def active_consent_subject_ids(
    connection: sqlite3.Connection, *, tenant_id: str, purpose: str, cutoff: str
) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT subject_id FROM consents WHERE tenant_id = ? AND purpose = ?"
        " AND status = 'active' AND granted_at <= ?"
        " AND (revoked_at IS NULL OR revoked_at > ?)",
        (tenant_id, purpose, cutoff, cutoff),
    ).fetchall()
    return tuple(str(row["subject_id"]) for row in rows)


def shadow_model_version(
    connection: sqlite3.Connection, *, tenant_id: str, track_id: str
) -> sqlite3.Row | None:
    """Versión en estado `shadow` de un track, si `tools/train` publicó alguna."""
    return connection.execute(
        "SELECT * FROM model_versions WHERE tenant_id = ? AND track_id = ? AND state = 'shadow'"
        " ORDER BY state_changed_at DESC LIMIT 1",
        (tenant_id, track_id),
    ).fetchone()


def catalog_version_row(
    connection: sqlite3.Connection, *, tenant_id: str, catalog_version: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM catalog_versions WHERE tenant_id = ? AND catalog_version = ?",
        (tenant_id, catalog_version),
    ).fetchone()


def recommendation_set_rows(
    connection: sqlite3.Connection, *, recommendation_set_version_ids: tuple[str, ...]
) -> list[sqlite3.Row]:
    if not recommendation_set_version_ids:
        return []
    placeholders = ",".join("?" for _ in recommendation_set_version_ids)
    return list(
        connection.execute(
            "SELECT * FROM recommendation_set_versions"
            f" WHERE recommendation_set_version_id IN ({placeholders})",
            recommendation_set_version_ids,
        ).fetchall()
    )


def strategy_version_rows(
    connection: sqlite3.Connection, *, strategy_version_ids: tuple[str, ...]
) -> list[sqlite3.Row]:
    if not strategy_version_ids:
        return []
    placeholders = ",".join("?" for _ in strategy_version_ids)
    return list(
        connection.execute(
            f"SELECT * FROM strategy_versions WHERE strategy_version_id IN ({placeholders})",
            strategy_version_ids,
        ).fetchall()
    )


def citations_for_strategies(
    connection: sqlite3.Connection, *, strategy_version_ids: tuple[str, ...]
) -> list[sqlite3.Row]:
    if not strategy_version_ids:
        return []
    placeholders = ",".join("?" for _ in strategy_version_ids)
    return list(
        connection.execute(
            "SELECT c.*, k.chunk_sha256 FROM strategy_citations AS c"
            " JOIN document_chunks AS k ON k.document_chunk_id = c.document_chunk_id"
            f" WHERE c.strategy_version_id IN ({placeholders})"
            " ORDER BY c.strategy_version_id, c.citation_id",
            strategy_version_ids,
        ).fetchall()
    )
