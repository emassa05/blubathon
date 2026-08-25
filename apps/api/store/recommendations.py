"""Instancias, reviews, planes humanos, ejecuciones y solicitudes de autoría.

SPEC 9.8, 10.1-10.3, 11.6 y 12.2. La instancia es inmutable y se crea junto con
el episodio; los GET posteriores solo leen. La review no vive en la instancia:
la ausencia de review activa significa `pending`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.canonical import content_hash
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.contracts.enums import ReviewDecision, RuntimeStatus
from apps.api.store.json_columns import dump, load_list
from apps.api.store.projection import project_as_of
from apps.api.store.sealing import seal


@dataclass(frozen=True, slots=True)
class NewInstance:
    tenant_id: str
    subject_id: str
    prediction_episode_id: str
    scenario_hash: str
    scenario_schema_version: str
    scenario_builder_version: str
    scenario_payload: dict[str, Any]
    catalog_version: str | None
    corpus_version: str | None
    strategy_version_ids: tuple[str, ...]
    runtime_status: str
    abstention_reasons: tuple[str, ...]
    availability_reason: str
    created_at: str
    cipher_key: bytes


def create_instance(connection: sqlite3.Connection, new: NewInstance) -> str:
    recommendation_instance_id = str(uuid4())
    connection.execute(
        "INSERT INTO recommendation_instances(recommendation_instance_id, tenant_id,"
        " subject_id, prediction_episode_id, scenario_hash, scenario_schema_version,"
        " scenario_builder_version, encrypted_scenario, catalog_version, corpus_version,"
        " strategy_version_ids, runtime_status, abstention_reasons, availability_reason,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            recommendation_instance_id,
            new.tenant_id,
            new.subject_id,
            new.prediction_episode_id,
            new.scenario_hash,
            new.scenario_schema_version,
            new.scenario_builder_version,
            seal(new.scenario_payload, new.cipher_key),
            new.catalog_version,
            new.corpus_version,
            dump(list(new.strategy_version_ids)),
            new.runtime_status,
            dump(sorted(new.abstention_reasons)),
            new.availability_reason,
            new.created_at,
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


def instance_strategy_ids(row: sqlite3.Row) -> tuple[str, ...]:
    return tuple(load_list(row["strategy_version_ids"]))


def create_authoring_request(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    prediction_episode_id: str,
    scenario_hash: str,
    scenario_schema_version: str,
    scenario_payload: dict[str, Any],
    reason: str,
    catalog_version: str | None,
    created_at: str,
    cipher_key: bytes,
) -> str | None:
    """SPEC 9.8: se deduplica por tenant, sujeto, hash y catálogo mientras esté abierta."""
    existing = connection.execute(
        "SELECT authoring_request_id FROM authoring_requests"
        " WHERE tenant_id = ? AND subject_id = ? AND scenario_hash = ?"
        " AND COALESCE(catalog_version, '') = COALESCE(?, '') AND status = 'open'",
        (tenant_id, subject_id, scenario_hash, catalog_version),
    ).fetchone()
    if existing is not None:
        return existing["authoring_request_id"]

    authoring_request_id = str(uuid4())
    connection.execute(
        "INSERT INTO authoring_requests(authoring_request_id, tenant_id, subject_id,"
        " prediction_episode_id, scenario_hash, scenario_schema_version, encrypted_scenario,"
        " reason, catalog_version, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)",
        (
            authoring_request_id,
            tenant_id,
            subject_id,
            prediction_episode_id,
            scenario_hash,
            scenario_schema_version,
            seal(scenario_payload, cipher_key),
            reason,
            catalog_version,
            created_at,
        ),
    )
    return authoring_request_id


# -- reviews -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NewReview:
    tenant_id: str
    recommendation_instance_id: str
    strategy_version_id: str
    decision: str
    reviewed_by: str
    reviewer_role: str
    reviewed_at: str
    human_plan_version_id: str | None
    supersedes_id: str | None
    ingested_at: str


def insert_review(connection: sqlite3.Connection, new: NewReview) -> str:
    review_id = str(uuid4())
    connection.execute(
        "INSERT INTO recommendation_reviews(review_id, tenant_id,"
        " recommendation_instance_id, strategy_version_id, decision, reviewed_by,"
        " reviewer_role, reviewed_at, human_plan_version_id, supersedes_id, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            review_id,
            new.tenant_id,
            new.recommendation_instance_id,
            new.strategy_version_id,
            new.decision,
            new.reviewed_by,
            new.reviewer_role,
            new.reviewed_at,
            new.human_plan_version_id,
            new.supersedes_id,
            new.ingested_at,
        ),
    )
    return review_id


def active_reviews(
    connection: sqlite3.Connection, *, recommendation_instance_id: str, cutoff: str
) -> dict[str, dict[str, Any]]:
    """Review activa por estrategia. Sin fila activa, la estrategia está pending."""
    rows = connection.execute(
        "SELECT * FROM recommendation_reviews WHERE recommendation_instance_id = ?",
        (recommendation_instance_id,),
    ).fetchall()
    projection = project_as_of((dict(row) for row in rows), cutoff, id_field="review_id")
    latest: dict[str, dict[str, Any]] = {}
    for row in projection.leaves:
        key = row["strategy_version_id"]
        current = latest.get(key)
        if current is None or (row["reviewed_at"], row["review_id"]) > (
            current["reviewed_at"],
            current["review_id"],
        ):
            latest[key] = row
    return latest


def review(connection: sqlite3.Connection, review_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM recommendation_reviews WHERE review_id = ?", (review_id,)
    ).fetchone()


def create_human_plan(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    recommendation_instance_id: str,
    replaced_strategy_version_id: str,
    action_text_es: str,
    author_actor_id: str,
    allowed_executor_roles: tuple[str, ...],
    created_at: str,
) -> str:
    """SPEC 10.2: inmutable, sin citas RAG y con roles subconjunto de la estrategia."""
    previous = connection.execute(
        "SELECT COALESCE(MAX(plan_version), 0) AS last FROM human_plan_versions"
        " WHERE recommendation_instance_id = ? AND replaced_strategy_version_id = ?",
        (recommendation_instance_id, replaced_strategy_version_id),
    ).fetchone()
    plan_version = int(previous["last"]) + 1
    human_plan_version_id = str(uuid4())
    payload = {
        "recommendation_instance_id": recommendation_instance_id,
        "replaced_strategy_version_id": replaced_strategy_version_id,
        "action_text_es": action_text_es,
        "allowed_executor_roles": sorted(allowed_executor_roles),
        "plan_version": plan_version,
    }
    connection.execute(
        "INSERT INTO human_plan_versions(human_plan_version_id, tenant_id,"
        " recommendation_instance_id, replaced_strategy_version_id, action_text_es,"
        " author_actor_id, allowed_executor_roles, plan_version, content_sha256, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            human_plan_version_id,
            tenant_id,
            recommendation_instance_id,
            replaced_strategy_version_id,
            action_text_es,
            author_actor_id,
            dump(sorted(allowed_executor_roles)),
            plan_version,
            content_hash("human_plan_version", SPEC_VERSION, payload),
            created_at,
        ),
    )
    return human_plan_version_id


def human_plan(connection: sqlite3.Connection, human_plan_version_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM human_plan_versions WHERE human_plan_version_id = ?",
        (human_plan_version_id,),
    ).fetchone()


# -- ejecuciones ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NewExecution:
    tenant_id: str
    recommendation_instance_id: str
    strategy_version_id: str | None
    human_plan_version_id: str | None
    status: str
    actor_id: str
    actor_role: str
    recorded_at: str
    applied_at: str | None
    supersedes_id: str | None
    ingested_at: str


def insert_execution(connection: sqlite3.Connection, new: NewExecution) -> str:
    strategy_execution_id = str(uuid4())
    connection.execute(
        "INSERT INTO strategy_executions(strategy_execution_id, tenant_id,"
        " recommendation_instance_id, strategy_version_id, human_plan_version_id, status,"
        " actor_id, actor_role, recorded_at, applied_at, supersedes_id, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            strategy_execution_id,
            new.tenant_id,
            new.recommendation_instance_id,
            new.strategy_version_id,
            new.human_plan_version_id,
            new.status,
            new.actor_id,
            new.actor_role,
            new.recorded_at,
            new.applied_at,
            new.supersedes_id,
            new.ingested_at,
        ),
    )
    return strategy_execution_id


def active_executions(
    connection: sqlite3.Connection, *, recommendation_instance_id: str, cutoff: str
) -> tuple[dict[str, Any], ...]:
    rows = connection.execute(
        "SELECT * FROM strategy_executions WHERE recommendation_instance_id = ?",
        (recommendation_instance_id,),
    ).fetchall()
    projection = project_as_of(
        (dict(row) for row in rows), cutoff, id_field="strategy_execution_id"
    )
    return projection.leaves


def active_execution_id(
    connection: sqlite3.Connection,
    *,
    recommendation_instance_id: str,
    strategy_version_id: str | None,
    human_plan_version_id: str | None,
    cutoff: str,
) -> str | None:
    """Hoja vigente de ese ítem, que una corrección pasa a superseder."""
    for row in active_executions(
        connection, recommendation_instance_id=recommendation_instance_id, cutoff=cutoff
    ):
        if (
            row["strategy_version_id"] == strategy_version_id
            and row["human_plan_version_id"] == human_plan_version_id
        ):
            return str(row["strategy_execution_id"])
    return None


def execution(connection: sqlite3.Connection, strategy_execution_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM strategy_executions WHERE strategy_execution_id = ?",
        (strategy_execution_id,),
    ).fetchone()


# -- concurrencia --------------------------------------------------------


def revision_etag(
    connection: sqlite3.Connection, *, recommendation_instance_id: str, cutoff: str
) -> str:
    """`If-Match` sobre el estado de revisión de la instancia (SPEC 11.2)."""
    reviews = active_reviews(
        connection, recommendation_instance_id=recommendation_instance_id, cutoff=cutoff
    )
    executions = active_executions(
        connection, recommendation_instance_id=recommendation_instance_id, cutoff=cutoff
    )
    payload = {
        "recommendation_instance_id": recommendation_instance_id,
        "reviews": sorted(
            (row["strategy_version_id"], row["review_id"], row["decision"])
            for row in reviews.values()
        ),
        "executions": sorted((row["strategy_execution_id"], row["status"]) for row in executions),
    }
    return content_hash("recommendation_instance_revision", SPEC_VERSION, payload)


def pending_instance_ids(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_ids: tuple[str, ...],
    cutoff: str,
) -> list[sqlite3.Row]:
    """Inbox filtrado en SQL por tenant y por los sujetos con grant activo.

    Una instancia entra al inbox si tiene al menos una estrategia sin review
    activa. La ausencia de review es lo que significa `pending` (SPEC 10.1).
    """
    if not subject_ids:
        return []
    placeholders = ",".join("?" for _ in subject_ids)
    return connection.execute(
        "SELECT i.* FROM recommendation_instances AS i"
        f" WHERE i.tenant_id = ? AND i.subject_id IN ({placeholders})"
        " AND i.runtime_status = ?"
        " AND EXISTS ("
        "   SELECT 1 FROM json_each(i.strategy_version_ids) AS s"
        "   WHERE NOT EXISTS ("
        "     SELECT 1 FROM recommendation_reviews AS r"
        "     WHERE r.recommendation_instance_id = i.recommendation_instance_id"
        "       AND r.strategy_version_id = s.value"
        "       AND r.ingested_at <= ?"
        "       AND NOT EXISTS (SELECT 1 FROM recommendation_reviews AS newer"
        "                       WHERE newer.supersedes_id = r.review_id"
        "                         AND newer.ingested_at <= ?)))"
        " ORDER BY i.created_at DESC, i.recommendation_instance_id",
        (tenant_id, *subject_ids, RuntimeStatus.MATCHED.value, cutoff, cutoff),
    ).fetchall()


def is_favourable(decision: str) -> bool:
    """Solo `approved` y `human_plan_substituted` exponen algo al cuidador."""
    return decision in (
        ReviewDecision.APPROVED.value,
        ReviewDecision.HUMAN_PLAN_SUBSTITUTED.value,
    )
