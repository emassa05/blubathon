"""Auditoría append-only sin payload clínico (SPEC 13.2, CONVENTIONS 15)."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

from apps.api.auth.context import ActorContext


def record(
    connection: sqlite3.Connection,
    *,
    actor: ActorContext | None,
    action: str,
    resource_type: str,
    decision: str,
    occurred_at: str,
    request_id: str,
    resource_id: str | None = None,
    subject_id: str | None = None,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    reason_code: str | None = None,
) -> str:
    """Registra un evento. Solo identificadores y códigos: nunca valores clínicos."""
    audit_event_id = str(uuid4())
    connection.execute(
        "INSERT INTO audit_events(audit_event_id, tenant_id, actor_id, action,"
        " resource_type, resource_id, subject_id, decision, reason_code, request_id,"
        " occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            audit_event_id,
            tenant_id if tenant_id is not None else (actor.tenant_id if actor else None),
            actor_id if actor_id is not None else (actor.actor_id if actor else None),
            action,
            resource_type,
            resource_id,
            subject_id,
            decision,
            reason_code,
            request_id,
            occurred_at,
        ),
    )
    return audit_event_id
