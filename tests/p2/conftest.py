"""Fixtures de P2: base sembrada, reloj congelado y cliente HTTP.

Los datos son ficticios (`tools/seed`); ningún test versionado usa un export
real (CONVENTIONS 15).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient

from apps.api.clock import FrozenClock
from apps.api.main import create_app
from apps.api.settings import Settings
from tools.seed import ids
from tools.seed.seeder import seed

START = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(START)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "faro-test.db",
        audit_secret=b"faro-test-audit-secret",
        scenario_secret=b"faro-test-scenario-secret",
    )


@pytest.fixture
def catalog_profile() -> Literal["blocked", "fixture-active"]:
    """Por defecto el estado honesto: sin revisor clínico autorizado."""
    return "blocked"


@pytest.fixture
def app(settings: Settings, clock: FrozenClock, catalog_profile: str):
    application = create_app(settings=settings, clock=clock)
    registry = application.state.registry
    with registry.core.database.write() as connection:
        seed(connection, catalog_profile=catalog_profile)  # type: ignore[arg-type]
    yield application
    registry.core.database.close()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app):
    return app.state.registry.core.database


class Caller:
    """Cliente tipado por actor: añade el token demo y la clave idempotente."""

    def __init__(self, client: TestClient, token: str) -> None:
        self._client = client
        self._token = token
        self._counter = 0

    def _headers(self, key: str | None, if_match: str | None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if key is not None:
            headers["Idempotency-Key"] = key
        if if_match is not None:
            headers["If-Match"] = if_match
        return headers

    def next_key(self) -> str:
        self._counter += 1
        return f"key-{self._token}-{self._counter}"

    def get(self, path: str, **params: Any):
        return self._client.get(path, headers=self._headers(None, None), params=params)

    def post(
        self,
        path: str,
        json: Any = None,
        *,
        key: str | None = None,
        if_match: str | None = None,
    ):
        return self._client.post(
            path,
            json=json,
            headers=self._headers(key or self.next_key(), if_match),
        )

    def post_raw(self, path: str, json: Any = None, *, headers: dict[str, str] | None = None):
        merged = {"Authorization": f"Bearer {self._token}"}
        merged.update(headers or {})
        return self._client.post(path, json=json, headers=merged)


@pytest.fixture
def caregiver(client: TestClient) -> Caller:
    return Caller(client, ids.TOKENS[ids.CAREGIVER_A])


@pytest.fixture
def professional(client: TestClient) -> Caller:
    return Caller(client, ids.TOKENS[ids.PROFESSIONAL_A])


@pytest.fixture
def other_tenant_caregiver(client: TestClient) -> Caller:
    return Caller(client, ids.TOKENS[ids.CAREGIVER_B])


@pytest.fixture
def evaluator(client: TestClient) -> Caller:
    return Caller(client, ids.TOKENS[ids.MODEL_EVALUATOR_A])


@pytest.fixture
def unaccredited_professional(client: TestClient) -> Caller:
    return Caller(client, ids.TOKENS[ids.UNACCREDITED_PROFESSIONAL_A])
