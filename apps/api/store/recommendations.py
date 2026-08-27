"""Persistence for live recommendation generation and feedback."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

from apps.api.store.json_columns import dump, load_list


def create_pending(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    prediction_episode_id: str,
    risk_band: str,
    query_es: str,
    now: str,
) -> str:
    recommendation_instance_id = str(uuid4())
    connection.execute(
        "INSERT INTO recommendation_instances(recommendation_instance_id, tenant_id,"
        " subject_id, prediction_episode_id, risk_band, query_es, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
        (
            recommendation_instance_id,
            tenant_id,
            subject_id,
            prediction_episode_id,
            risk_band,
            query_es,
            now,
            now,
        ),
    )
    return recommendation_instance_id


def instance(connection: sqlite3.Connection, recommendation_instance_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM recommendation_instances WHERE recommendation_instance_id = ?",
        (recommendation_instance_id,),
    ).fetchone()


def instance_for_episode(
    connection: sqlite3.Connection, prediction_episode_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM recommendation_instances WHERE prediction_episode_id = ?",
        (prediction_episode_id,),
    ).fetchone()


def update_result(
    connection: sqlite3.Connection,
    *,
    recommendation_instance_id: str,
    risk_band: str,
    query_es: str,
    status: str,
    action_text_es: str | None,
    purpose_es: str | None,
    citations: list[dict],
    abstention_reason: str | None,
    now: str,
    increment_attempt: bool = False,
) -> None:
    connection.execute(
        "UPDATE recommendation_instances SET risk_band = ?, query_es = ?, status = ?,"
        " action_text_es = ?, purpose_es = ?, citations = ?, abstention_reason = ?,"
        " updated_at = ?, attempt = attempt + ? WHERE recommendation_instance_id = ?",
        (
            risk_band,
            query_es,
            status,
            action_text_es,
            purpose_es,
            dump(citations),
            abstention_reason,
            now,
            int(increment_attempt),
            recommendation_instance_id,
        ),
    )


def list_instances(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    status: str | None,
    subject_id: str | None,
    limit: int,
) -> list[sqlite3.Row]:
    clauses = ["i.tenant_id = ?"]
    parameters: list[object] = [tenant_id]
    if status is not None:
        clauses.append("i.status = ?")
        parameters.append(status)
    if subject_id is not None:
        clauses.append("i.subject_id = ?")
        parameters.append(subject_id)
    parameters.append(limit)
    return list(
        connection.execute(
            "SELECT i.*, s.display_label AS child_label, f.local_date"
            " FROM recommendation_instances AS i"
            " JOIN subjects AS s ON s.subject_id = i.subject_id"
            " JOIN prediction_episodes AS e ON e.prediction_episode_id = i.prediction_episode_id"
            " JOIN form_sessions AS f ON f.form_session_id = e.form_session_id"
            f" WHERE {' AND '.join(clauses)} ORDER BY i.created_at DESC LIMIT ?",
            parameters,
        ).fetchall()
    )


def latest_feedback(
    connection: sqlite3.Connection, recommendation_instance_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM recommendation_feedback WHERE recommendation_instance_id = ?"
        " ORDER BY created_at DESC, feedback_id DESC LIMIT 1",
        (recommendation_instance_id,),
    ).fetchone()


def add_feedback(
    connection: sqlite3.Connection,
    *,
    recommendation_instance_id: str,
    rating: str,
    note_es: str | None,
    now: str,
) -> str:
    feedback_id = str(uuid4())
    connection.execute(
        "INSERT INTO recommendation_feedback(feedback_id, recommendation_instance_id, rating,"
        " note_es, created_at) VALUES (?, ?, ?, ?, ?)",
        (feedback_id, recommendation_instance_id, rating, note_es, now),
    )
    return feedback_id


def indexed_chunk_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT c.*, d.title AS document_title, d.canonical_url"
            " FROM document_chunks AS c JOIN document_versions AS d"
            " ON d.document_version_id = c.document_version_id"
            " WHERE d.status IN ('indexed', 'active') ORDER BY c.document_chunk_id"
        ).fetchall()
    )


def citation_chunk_ids(row: sqlite3.Row) -> frozenset[str]:
    return frozenset(
        str(citation["document_chunk_id"])
        for citation in load_list(row["citations"])
        if citation.get("document_chunk_id")
    )
