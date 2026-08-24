"""The Bluba export becomes canonical DailyLog records (SPEC 2.1, adapter)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ml.adapters.bluba import (
    BLUBA_GI_STATUS,
    BLUBA_MEDICATION_ADHERENCE,
    BLUBA_SLEEP_QUALITY,
    BLUBA_WAKE_STATE,
    build_bluba_logs,
    deterministic_uuid4,
)
from ml.errors import ContractViolationError
from packages.shared import DailyLog, MedicationAdherence

BLUBA_DIR = Path(__file__).resolve().parents[2] / "Datos base"

pytestmark = pytest.mark.filterwarnings("ignore")


def _rows(name: str) -> list[dict]:
    path = BLUBA_DIR / name
    if not path.exists():
        pytest.skip(f"{path} is not present")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


@pytest.fixture(scope="module")
def bluba_logs() -> list[dict]:
    return build_bluba_logs(
        _rows("4_seguimiento_diario_tutor.csv"),
        _rows("3_sesiones_profesionales.csv"),
        _rows("5_eventos_desregulacion_tutor.csv"),
    )


def test_every_row_validates_against_the_contract(bluba_logs):
    """The whole point: Bluba data becomes contract-valid without exceptions."""
    assert bluba_logs
    for log in bluba_logs:
        DailyLog.model_validate(log)


def test_the_four_cases_become_four_children(bluba_logs):
    assert len({log["child_id"] for log in bluba_logs}) == 4


def test_identifiers_are_stable_across_runs():
    """SPEC rule 0.9: two seedings must produce the same child ids."""
    assert deterministic_uuid4("child", "PAC-001") == deterministic_uuid4("child", "PAC-001")
    assert deterministic_uuid4("child", "PAC-001") != deterministic_uuid4("child", "PAC-002")
    assert DailyLog.model_fields["child_id"].annotation is not None


def test_tutor_and_therapy_rows_use_their_own_source(bluba_logs):
    """SPEC 2.3: a therapy record may only carry what a therapist observed."""
    sources = {log["source"] for log in bluba_logs}
    assert sources == {"home", "therapy"}
    for log in bluba_logs:
        if log["source"] == "therapy":
            assert "sleep_quality" not in log or log.get("sleep_quality") is None


def test_only_a_severe_event_becomes_a_crisis(bluba_logs):
    """SPEC rule 0.7: the absence of a logged event is not evidence of calm."""
    labelled = [log for log in bluba_logs if log.get("crisis_occurred") is True]
    assert len(labelled) == 2, "the export contains exactly two severe events"
    assert all(log.get("crisis_occurred") in (True, None) for log in bluba_logs)


def test_medication_adherence_keeps_three_states(bluba_logs):
    """not_applicable is an answer, and never collapses into a null."""
    values = {log.get("medication_adherence") for log in bluba_logs if log["source"] == "home"}
    assert MedicationAdherence.NOT_APPLICABLE.value in values
    assert MedicationAdherence.TAKEN.value in values


def test_each_bluba_level_maps_to_a_distinct_canonical_value():
    """A three-level vocabulary must not lose a level on the way in."""
    for table in (BLUBA_SLEEP_QUALITY, BLUBA_WAKE_STATE, BLUBA_GI_STATUS):
        assert len(set(table.values())) == len(table)
    assert set(BLUBA_MEDICATION_ADHERENCE.values()) == {
        member.value for member in MedicationAdherence
    }


def test_an_event_without_a_tutor_log_still_becomes_a_day(bluba_logs):
    """The NMAR case: something happened on a day nobody filled in."""
    event_only = [
        log
        for log in bluba_logs
        if log["source"] == "home"
        and log.get("relevant_event_flag")
        and log.get("sleep_quality") is None
    ]
    assert event_only, "the export has one event on a day with no tutor row"


def test_an_unknown_category_is_refused():
    with pytest.raises(ContractViolationError):
        build_bluba_logs(
            [{"id_caso": "PAC-001", "fecha": "2026-07-01", "modo_despertar": "Radiante"}]
        )


def test_a_duplicate_day_is_refused():
    row = {"id_caso": "PAC-001", "fecha": "2026-07-01"}
    with pytest.raises(ContractViolationError):
        build_bluba_logs([row, dict(row)])


def test_the_adapter_is_deterministic(bluba_logs):
    again = build_bluba_logs(
        _rows("4_seguimiento_diario_tutor.csv"),
        _rows("3_sesiones_profesionales.csv"),
        _rows("5_eventos_desregulacion_tutor.csv"),
    )
    assert again == bluba_logs
