"""§2.5 — `provenance='assumed_stable'` con valor no nulo -> ContractViolationError."""

import pytest

from apps.api.store.repository import insert_log
from ml.errors import ContractViolationError
from packages.shared.models import DailyLog


def test_s2_5_pydantic_rechaza_assumed_stable_con_valor():
    with pytest.raises(ContractViolationError):
        DailyLog(
            child_id="c1",
            date="2026-08-01",
            source="home",
            gi_status=4,
            field_provenance={"gi_status": "assumed_stable"},
        )


def test_s2_5_store_rechaza_assumed_stable_con_valor(db_conn):
    with pytest.raises(ContractViolationError):
        insert_log(
            db_conn,
            {
                "child_id": "c1",
                "date": "2026-08-01",
                "source": "home",
                "gi_status": 4,
                "field_provenance": {"gi_status": "assumed_stable"},
            },
        )


def test_s2_5_assumed_stable_sin_valor_es_valido():
    log = DailyLog(
        child_id="c1",
        date="2026-08-01",
        source="home",
        gi_status=None,
        field_provenance={"gi_status": "assumed_stable"},
    )
    assert log.gi_status is None
