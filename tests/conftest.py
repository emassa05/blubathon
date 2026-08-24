"""Shared fixtures: one small trained model, reused by the whole session.

Training is the slow part, so it happens once per test run on the smallest
cohort the contract allows (conformal calibration needs ten validation
children, which needs a hundred in total). Everything downstream -- the API
client, the Value-of-Information scorer -- hangs off that single model.
"""

from __future__ import annotations

import json
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from ml.engine.pipeline import PointInTimeFeatures, make_override_scorer
from ml.spec_constants import MODEL_MIN_SPLIT_CHILDREN
from ml.synth.generate import generate_synthetic_data
from ml.train import TrainedModel, train

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
BLUBA_DIR = Path(__file__).resolve().parents[1] / "Datos base"

# Smallest cohort that satisfies the split rules of SPEC 9.4 while staying fast.
TEST_CHILDREN = 100
TEST_DAYS = 45


@pytest.fixture(scope="session")
def synthetic_dataset():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return generate_synthetic_data(n_children=TEST_CHILDREN, days=TEST_DAYS)


@pytest.fixture(scope="session")
def trained_model(synthetic_dataset) -> TrainedModel:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return train(
            synthetic_dataset.logs,
            synthetic_dataset.ground_truth,
            evaluate=True,
            misspecification=False,
        )


@pytest.fixture(scope="session")
def ensemble(trained_model):
    return trained_model.ensemble


@pytest.fixture(scope="session")
def population_prior(trained_model):
    return trained_model.population_prior


def _load_fixture(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def calm_history() -> list[dict[str, Any]]:
    return _load_fixture("child_calm.json")


@pytest.fixture
def high_risk_history() -> list[dict[str, Any]]:
    return _load_fixture("child_high_risk.json")


@pytest.fixture
def abstain_history() -> list[dict[str, Any]]:
    return _load_fixture("child_abstain.json")


def last_date(history: list[dict[str, Any]]) -> date:
    return date.fromisoformat(max(log["date"] for log in history))


@pytest.fixture
def scorer_factory(ensemble):
    """Build a batched override scorer for one child-day, as the API does."""

    def build(history: list[dict[str, Any]], target_date: date | str | None = None):
        target = target_date or last_date(history)
        child_id = history[0]["child_id"]
        context = PointInTimeFeatures(history, child_id, target)
        return make_override_scorer(ensemble, context), context

    return build


@pytest.fixture
def db_conn(tmp_path):
    from apps.api.store import get_connection, init_db

    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory, synthetic_dataset) -> Path:
    """A database holding the fixture children plus the Bluba cases."""
    from apps.api.store import get_connection, init_db
    from apps.api.store.seed import seed_from_bluba, seed_from_fixtures

    db_path = tmp_path_factory.mktemp("faro") / "faro.db"
    conn = get_connection(db_path)
    init_db(conn)
    seed_from_fixtures(conn, FIXTURES_DIR)
    if BLUBA_DIR.exists():
        seed_from_bluba(conn, BLUBA_DIR)
    conn.close()
    return db_path


@pytest.fixture
def services(trained_model, seeded_db):
    from apps.api.services_impl import FaroServices

    return FaroServices("unused", seeded_db, loader=lambda _: trained_model)


@pytest.fixture
def client(services):
    from fastapi.testclient import TestClient

    from apps.api.main import app
    from apps.api.services import configure_services

    configure_services(services)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def calm_child_id(calm_history) -> str:
    return calm_history[0]["child_id"]


@pytest.fixture
def high_risk_child_id(high_risk_history) -> str:
    return high_risk_history[0]["child_id"]


@pytest.fixture
def abstain_child_id(abstain_history) -> str:
    return abstain_history[0]["child_id"]


def next_day(value: date | str) -> str:
    day = value if isinstance(value, date) else date.fromisoformat(value)
    return (day + timedelta(days=1)).isoformat()


__all__ = ["MODEL_MIN_SPLIT_CHILDREN", "last_date", "next_day"]
