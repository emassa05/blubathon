"""Adaptadores hacia el dominio de P1.

Hoy el backend corre contra `mock`: respuestas fixture deterministas detrás de
los puertos. Cuando P1 publique `ml/**` y `rag/runtime`, `p1.build_ports()`
sustituye al mock sin tocar servicios, store ni UI.

`FARO_P1_ADAPTERS=real` fuerza el conjunto real; por defecto se usa el mock y la
respuesta de cada endpoint declara qué origen se usó.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from apps.api.ports import DefaultsPort, FormPort, PredictionPort, RagRuntimePort


@dataclass(frozen=True, slots=True)
class Ports:
    defaults: DefaultsPort
    form: FormPort
    prediction: PredictionPort
    rag: RagRuntimePort
    source: str


def build_ports(source: str | None = None, *, secret: bytes = b"faro-demo-audit-secret") -> Ports:
    chosen = source or os.environ.get("FARO_P1_ADAPTERS", "mock")
    if chosen == "real":
        from apps.api.adapters.p1 import build_real_ports

        return build_real_ports()
    if chosen != "mock":
        raise ValueError(f"conjunto de adaptadores desconocido: {chosen}")
    from apps.api.adapters.mock import build_mock_ports

    return build_mock_ports(secret=secret)
