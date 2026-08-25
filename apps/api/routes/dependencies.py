"""Dependencias de ruta: estado de la app, actor autenticado y cabeceras."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from apps.api.auth.context import ActorContext
from apps.api.auth.demo import authenticate
from apps.api.errors import FaroApiError
from apps.api.services import ServiceRegistry


def registry(request: Request) -> ServiceRegistry:
    return request.app.state.registry


def current_actor(
    request: Request,
    services: Annotated[ServiceRegistry, Depends(registry)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> ActorContext:
    with services.core.database.read() as connection:
        return authenticate(
            connection,
            authorization_header=authorization,
            request_id=request.state.request_id,
            mode=services.core.settings.deployment_mode,
        )


def idempotency_key(
    key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    """SPEC 11.2: todo POST exige `Idempotency-Key`."""
    if key is None or not key.strip():
        raise FaroApiError("idempotency_key_required", 400)
    return key.strip()


def if_match(
    value: Annotated[str | None, Header(alias="If-Match")] = None,
) -> str | None:
    return value


Registry = Annotated[ServiceRegistry, Depends(registry)]
Actor = Annotated[ActorContext, Depends(current_actor)]
IdempotencyKey = Annotated[str, Depends(idempotency_key)]
IfMatch = Annotated[str | None, Depends(if_match)]
