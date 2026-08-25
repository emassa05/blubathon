"""Identidad autenticada de una request.

`tenant_id` viene siempre de la fila del usuario, nunca de una cabecera: un
cliente no puede declarar su organización (SPEC 13.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.api.contracts.enums import Role


@dataclass(frozen=True, slots=True)
class ActorContext:
    actor_id: str
    tenant_id: str
    display_name: str
    roles: frozenset[str]
    request_id: str

    def has_role(self, role: Role | str) -> bool:
        return str(role) in self.roles

    def has_any_role(self, *roles: Role | str) -> bool:
        return any(str(role) in self.roles for role in roles)
