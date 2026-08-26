"""Integration tests reuse the seeded v0.4 API fixtures."""

from tests.p2.conftest import (  # noqa: F401
    GroundedDraftTransport,
    app,
    caregiver,
    client,
    clock,
    db,
    settings,
)
