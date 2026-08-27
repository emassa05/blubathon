"""Selección del conjunto de adaptadores hacia el dominio de P1.

`BLUBATHON_P1_ADAPTERS=real` usa `ml/**` a través de
`apps/api/adapters/p1`; por defecto se usa `mock`, que sigue siendo el camino
seleccionable de test y demo y no calcula ninguna fórmula del SPEC.

La respuesta de cada sesión declara qué origen se usó (`adapters_source`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.api.ports import DefaultsPort, FormPort, PredictionPort

if TYPE_CHECKING:  # pragma: no cover - solo para tipos
    from apps.api.store.db import Database


@dataclass(frozen=True, slots=True)
class Ports:
    defaults: DefaultsPort
    form: FormPort
    prediction: PredictionPort
    source: str


def build_ports(
    source: str | None = None,
    *,
    secret: bytes = b"blubathon-demo-audit-secret",
    database: Database | None = None,
) -> Ports:
    chosen = source or os.environ.get("BLUBATHON_P1_ADAPTERS", "mock")
    if chosen == "real":
        from apps.api.adapters.p1 import build_real_ports

        return build_real_ports(database=database, secret=secret)
    if chosen != "mock":
        raise ValueError(f"conjunto de adaptadores desconocido: {chosen}")
    from apps.api.adapters.mock import build_mock_ports

    return build_mock_ports(secret=secret)
