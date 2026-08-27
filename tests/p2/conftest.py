"""Seeded v0.4 API fixtures."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.clock import FrozenClock
from apps.api.main import create_app
from apps.api.settings import Settings
from tools.seed import data, ids
from tools.seed.seeder import seed

START = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


# `render_fragments` numera cada fragmento como "[fragmento N]".
_FRAGMENT_TAG = re.compile(r"\[fragmento (\d+)\]\n(.+)")


class GroundedDraftTransport:
    """Parafrasea, y declara la procedencia leyéndola del prompt."""

    model_id = "fixture-draft"
    model_sha256 = "fixture-draft-sha256"

    def complete(self, prompt: str) -> str:
        candidates = (
            data.FIXTURE_CHUNKS[0]["text"],
            data.FIXTURE_CHUNKS[1]["text"],
        )
        fragment = next(
            int(match.group(1))
            for match in _FRAGMENT_TAG.finditer(prompt)
            if match.group(2).strip() in candidates
        )
        return json.dumps(
            {
                "purpose_es": "Ofrecer un apoyo cotidiano basado en la guía ficticia.",
                "action_text_es": "Prueben el apoyo descrito y observen cómo resulta.",
                "claims": [
                    {
                        "parafrasis_es": "La guía sugiere mirar el entorno antes de cambiar todo.",
                        "source_fragment": fragment,
                    }
                ],
            }
        )


class UngroundedDraftTransport(GroundedDraftTransport):
    """Cita un fragmento que no se entregó en el prompt."""

    def complete(self, prompt: str) -> str:
        beyond = len(_FRAGMENT_TAG.findall(prompt)) + 99
        return json.dumps(
            {
                "purpose_es": "Texto no sustentado.",
                "action_text_es": "Texto no sustentado.",
                "claims": [
                    {
                        "parafrasis_es": "Una idea que no salió de ningún fragmento.",
                        "source_fragment": beyond,
                    }
                ],
            }
        )


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(START)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "blubathon-test.db",
        audit_secret=b"blubathon-test-audit-secret",
        scenario_secret=b"blubathon-test-scenario-secret",
    )


@pytest.fixture
def app(settings: Settings, clock: FrozenClock):
    application = create_app(
        settings=settings, clock=clock, draft_transport=GroundedDraftTransport()
    )
    registry = application.state.registry
    with registry.core.database.write() as connection:
        seed(connection)
    yield application
    registry.core.database.close()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app):
    return app.state.registry.core.database


@pytest.fixture
def caregiver(client: TestClient) -> TestClient:
    return client


def submit_form(
    client: TestClient,
    child_id: str = str(ids.SUBJECT_ANA),
    *,
    answers: list[dict] | None = None,
):
    return client.post(
        f"/v1/children/{child_id}/forms",
        json={
            "source": "caregiver_daily",
            "local_date": "2026-08-25",
            "answers": answers
            or [
                {
                    "field_code": "sleep_quality",
                    "value": "interrupted",
                    "interaction": "manual",
                },
                {
                    "field_code": "routine_changes",
                    "value": True,
                    "interaction": "manual",
                },
            ],
        },
    )
