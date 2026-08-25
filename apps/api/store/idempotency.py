"""Almacén de claves idempotentes (SPEC 11.2, CONVENTIONS 12.3).

El scope es `(tenant_id, actor_id, method, normalized_concrete_path, key)` y lo
declara `packages.shared.IdempotencyScope`, cuyo validador rechaza un path que
sea el template de la ruta. Así la invariante no vive en un comentario: el
ejemplo inválido `idempotency.route_template_path` es su oráculo.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apps.api.contracts.models import IdempotencyScope, request_fingerprint
from apps.api.store.json_columns import dump, load


def normalize_path(path: str) -> str:
    """Path concreto normalizado: sin barra final y en minúsculas de ruta."""
    trimmed = path.rstrip("/")
    return trimmed or "/"


def scope(*, tenant_id: str, actor_id: str, method: str, path: str, key: str) -> IdempotencyScope:
    """SPEC 11.2. Un template de ruta no llega a construirse."""
    return IdempotencyScope(
        tenant_id=tenant_id,
        actor_id=actor_id,
        method=method,
        normalized_concrete_path=normalize_path(path),
        idempotency_key=key,
    )


def request_hash(
    request_scope: IdempotencyScope,
    *,
    path_params: dict[str, Any],
    query: dict[str, Any],
    body: Any,
) -> str:
    """Hash del scope, los path params, la query canónica y el body."""
    return request_fingerprint(
        request_scope,
        path_params={key: str(value) for key, value in sorted(path_params.items())},
        query={key: query[key] for key in sorted(query)},
        body=body,
    )


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
