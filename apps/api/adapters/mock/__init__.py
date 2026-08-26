"""Conjunto de adaptadores fixture que sustituye a P1 hasta H1.

Ninguna clase de este paquete implementa una fórmula del SPEC: no hay Beta, ni
Dirichlet, ni DQI, ni VoI, ni BM25, ni RRF. Devuelven datos de fixture o estados
`unavailable`, que es exactamente lo que el SPEC exige cuando un estimador no
está disponible. Así el resto del producto -sesiones, persistencia, autorización,
idempotencia y UI- se construye y se prueba sin inventar estadística.
"""

from __future__ import annotations

from apps.api.adapters import Ports
from apps.api.adapters.mock.defaults import MockDefaults
from apps.api.adapters.mock.form import MockForm
from apps.api.adapters.mock.prediction import MockPrediction

MOCK_SOURCE = "mock"


def build_mock_ports(*, secret: bytes = b"blubathon-demo-audit-secret") -> Ports:
    return Ports(
        defaults=MockDefaults(secret=secret),
        form=MockForm(),
        prediction=MockPrediction(),
        source=MOCK_SOURCE,
    )
