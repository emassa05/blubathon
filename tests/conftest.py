import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_db
from apps.api.main import app
from apps.api.store.db import get_connection, init_db
from apps.api.store.seed import seed_from_fixtures

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

CHILD_CALM = "00000000-0000-0000-0000-000000000001"
CHILD_HIGH = "00000000-0000-0000-0000-000000000002"
CHILD_ABSTAIN = "00000000-0000-0000-0000-000000000003"


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def calm_history() -> list[dict]:
    return _load("child_calm.json")


@pytest.fixture
def high_risk_history() -> list[dict]:
    return _load("child_high_risk.json")


@pytest.fixture
def abstain_history() -> list[dict]:
    return _load("child_abstain.json")


@pytest.fixture
def db_conn(tmp_path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(tmp_path):
    """TestClient con una SQLite temporal sembrada desde `fixtures/`."""
    db_path = tmp_path / "test_api.db"
    conn = get_connection(db_path)
    init_db(conn)
    seed_from_fixtures(conn, fixtures_dir=FIXTURES_DIR)

    def override_get_db():
        c = get_connection(db_path)
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    conn.close()
