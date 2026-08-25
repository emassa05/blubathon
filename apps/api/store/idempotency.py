"""Almacén de claves idempotentes (SPEC 11.2, CONVENTIONS 12.3).

El scope es `(tenant_id, actor_id, method, normalized_concrete_path, key)`. El
path concreto incluye todos los IDs normalizados, así que la misma clave sobre
dos IDs distintos produce dos recursos distintos y nunca comparte replay.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.canonical import content_hash
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.store.json_columns import dump, load

IDEMPOTENCY_ARTIFACT = "idempotent_request"


def normalize_path(path: str) -> str:
    """Path concreto normalizado: sin barra final y en minúsculas de ruta."""
    trimmed = path.rstrip("/")
    return trimmed or "/"


def request_hash(
    *,
    path_params: dict[str, Any],
    query: dict[str, Any],
    body: Any,
) -> str:
    """Hash JCS con separación de dominio sobre path params, query y body."""
    payload = {
        "path_params": {key: str(value) for key, value in sorted(path_params.items())},
        "query": {key: query[key] for key in sorted(query)},
        "body": body,
    }
    return content_hash(IDEMPOTENCY_ARTIFACT, SPEC_VERSION, payload)


@dataclass(frozen=True, slots=True)
class StoredResponse:
    status_code: int
    body: Any


def find(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    actor_id: str,
    method: str,
    path: str,
    key: str,
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM idempotency_keys WHERE tenant_id = ? AND actor_id = ?"
        " AND method = ? AND normalized_concrete_path = ? AND idempotency_key = ?",
        (tenant_id, actor_id, method, normalize_path(path), key),
    ).fetchone()


def remember(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    actor_id: str,
    method: str,
    path: str,
    key: str,
    request_sha256: str,
    status_code: int,
    body: Any,
    created_at: str,
) -> None:
    connection.execute(
        "INSERT INTO idempotency_keys(idempotency_key_id, tenant_id, actor_id, method,"
        " normalized_concrete_path, idempotency_key, request_sha256, response_status,"
        " response_body, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid4()),
            tenant_id,
            actor_id,
            method,
            normalize_path(path),
            key,
            request_sha256,
            status_code,
            dump(body),
            created_at,
        ),
    )


def stored_response(row: sqlite3.Row) -> StoredResponse:
    return StoredResponse(int(row["response_status"]), load(row["response_body"]))
