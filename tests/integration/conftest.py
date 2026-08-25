"""Journeys extremo a extremo sobre servicios falsos.

Reutiliza las fixtures de `tests/p2` para no duplicar el arranque de la app; los
datos siguen siendo ficticios (`tools/seed`).
"""

from __future__ import annotations

from tests.p2.conftest import (  # noqa: F401
    Caller,
    app,
    caregiver,
    catalog_profile,
    client,
    clock,
    db,
    evaluator,
    other_tenant_caregiver,
    professional,
    settings,
    unaccredited_professional,
)
