"""Sesión local ficticia preseeded (SPEC 12.3).

La demo no implementa OIDC: `Authorization: Bearer <demo_session_token>` busca
un usuario sembrado. El token no es un secreto de producción y el modo piloto
rechaza este autenticador.
"""

from __future__ import annotations

import sqlite3

from apps.api.auth.context import ActorContext
from apps.api.contracts.enums import DeploymentMode
from apps.api.errors import unauthenticated


def parse_bearer(header: str | None) -> str | None:
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def authenticate(
    connection: sqlite3.Connection,
    *,
    authorization_header: str | None,
    request_id: str,
    mode: DeploymentMode,
) -> ActorContext:
    if mode is not DeploymentMode.DEMO:
        # SPEC 12.3: el piloto exige OIDC; este autenticador no lo sustituye.
        raise unauthenticated("invalid_credentials")
    token = parse_bearer(authorization_header)
    if token is None:
        raise unauthenticated()
    row = connection.execute(
        "SELECT user_id, tenant_id, display_name FROM users WHERE demo_session_token = ?",
        (token,),
    ).fetchone()
    if row is None:
        raise unauthenticated("invalid_credentials")
    roles = connection.execute(
        "SELECT role FROM user_roles WHERE user_id = ? AND tenant_id = ?",
        (row["user_id"], row["tenant_id"]),
    ).fetchall()
    return ActorContext(
        actor_id=row["user_id"],
        tenant_id=row["tenant_id"],
        display_name=row["display_name"],
        roles=frozenset(item["role"] for item in roles),
        request_id=request_id,
    )
