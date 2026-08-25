"""Contenedor de servicios de aplicación e idempotencia (SPEC 11.2, CONVENTIONS 12).

Una ruta valida, autoriza, llama un servicio y serializa. El servicio abre una
transacción por comando, carga estado, llama dominio puro por los puertos,
persiste eventos y devuelve contrato.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from apps.api.adapters import Ports
from apps.api.auth.authorization import AuthorizationService
from apps.api.auth.context import ActorContext
from apps.api.canonical import canonical_timestamp
from apps.api.clock import Clock, system_clock
from apps.api.errors import conflict
from apps.api.settings import Settings
from apps.api.store import idempotency
from apps.api.store.db import Database


@dataclass(frozen=True, slots=True)
class IdempotentRequest:
    """Todo lo que entra en el scope y en el hash de un POST (SPEC 11.2)."""

    key: str
    method: str
    concrete_path: str
    path_params: dict[str, Any]
    query: dict[str, Any]
    body: Any


@dataclass(frozen=True, slots=True)
class CommandResult:
    status_code: int
    body: Any
    replayed: bool = False


class Services:
    def __init__(
        self,
        *,
        settings: Settings,
        database: Database,
        ports: Ports,
        clock: Clock = system_clock,
    ) -> None:
        self.settings = settings
        self.database = database
        self.ports = ports
        self.clock = clock
        self.authorization = AuthorizationService(allowed_cohort=settings.allowed_cohort)

    # -- reloj -----------------------------------------------------------

    def now(self) -> str:
        """Tiempo de servidor en bytes canónicos (SPEC 5.9)."""
        return canonical_timestamp(self.clock())

    # -- idempotencia ----------------------------------------------------

    def execute_command(
        self,
        *,
        actor: ActorContext,
        request: IdempotentRequest,
        authorize_replay: Callable[[sqlite3.Connection, str], None],
        execute: Callable[[sqlite3.Connection, str], tuple[int, Any]],
    ) -> CommandResult:
        """Ejecuta un POST exactamente una vez por clave y payload.

        - Misma clave y payload devuelve la respuesta original.
        - Misma clave con payload distinto devuelve 409.
        - Un replay vuelve a autorizar rol, accreditation, grant y capability con
          `authorize_replay` antes de devolver la respuesta guardada: si el grant
          ya no vale responde 403 y no revela la respuesta histórica. En el camino
          normal la autorización la hace el propio servicio, dentro de `execute`.
        """
        request_sha256 = idempotency.request_hash(
            path_params=request.path_params, query=request.query, body=request.body
        )
        with self.database.write() as connection:
            now = self.now()
            existing = idempotency.find(
                connection,
                tenant_id=actor.tenant_id,
                actor_id=actor.actor_id,
                method=request.method,
                path=request.concrete_path,
                key=request.key,
            )
            if existing is not None:
                if existing["request_sha256"] != request_sha256:
                    raise conflict("idempotency_key_conflict")
                authorize_replay(connection, now)
                stored = idempotency.stored_response(existing)
                return CommandResult(stored.status_code, stored.body, replayed=True)

            status_code, body = execute(connection, now)
            idempotency.remember(
                connection,
                tenant_id=actor.tenant_id,
                actor_id=actor.actor_id,
                method=request.method,
                path=request.concrete_path,
                key=request.key,
                request_sha256=request_sha256,
                status_code=status_code,
                body=body,
                created_at=now,
            )
            return CommandResult(status_code, body)
