"""Precedencia de disponibilidad del catálogo (SPEC 9.6).

Las razones son estables y no se colapsan entre sí: `clinical_review_unavailable`
nunca se reduce a `catalog_not_ready`, y ambiguo o suspendido fallan cerrado.
"""

from __future__ import annotations

import pytest

from tests.p2.test_episodes_and_outcomes import complete_session
from tools.seed import ids


def instance_of(caregiver, db):
    result = complete_session(caregiver)
    return db.connection.execute(
        "SELECT * FROM recommendation_instances WHERE prediction_episode_id = ?",
        (result["prediction_episode_id"],),
    ).fetchone()


def test_without_a_clinical_reviewer_the_runtime_abstains_with_its_own_reason(
    caregiver, db
) -> None:
    """El perfil de seed por defecto deja las estrategias en `evidence_reviewed`."""
    row = instance_of(caregiver, db)
    assert row["runtime_status"] == "abstained"
    assert row["availability_reason"] == "clinical_review_unavailable"
    assert row["catalog_version"] is None


def test_abstained_instance_is_served_as_status_abstained(caregiver) -> None:
    result = complete_session(caregiver)
    view = caregiver.get(
        f"/api/v1/prediction-episodes/{result['prediction_episode_id']}/recommendations"
    ).json()
    assert view["status"] == "abstained"
    assert view["items"] == []
    assert view["reasons"] == ["clinical_review_unavailable"]
    assert view["catalog_version"] is None


def test_missing_corpus_takes_precedence_over_every_other_reason(caregiver, db) -> None:
    with db.write() as connection:
        connection.execute("UPDATE corpus_versions SET status = 'draft'")
    row = instance_of(caregiver, db)
    assert row["availability_reason"] == "corpus_not_ready"


@pytest.mark.parametrize("catalog_profile", ["fixture-active"])
def test_two_active_catalogs_fail_closed_as_ambiguous(caregiver, db, catalog_profile) -> None:
    with db.write() as connection:
        row = connection.execute("SELECT * FROM catalog_versions LIMIT 1").fetchone()
        columns = list(row.keys())
        values = {key: row[key] for key in columns}
        values["catalog_version"] = "catalog-fixture-0.3.1"
        values["effective_from"] = "2026-02-01T00:00:00.000Z"
        connection.execute(
            f"INSERT INTO catalog_versions({', '.join(columns)})"
            f" VALUES ({', '.join('?' for _ in columns)})",
            tuple(values[key] for key in columns),
        )
    instance = instance_of(caregiver, db)
    assert instance["availability_reason"] == "catalog_ambiguous"
    assert instance["runtime_status"] == "abstained"


@pytest.mark.parametrize("catalog_profile", ["fixture-active"])
def test_a_suspended_catalog_reports_suspension_not_absence(caregiver, db, catalog_profile) -> None:
    with db.write() as connection:
        connection.execute(
            "UPDATE catalog_versions SET status = 'suspended',"
            " suspended_at = '2026-08-24T00:00:00.000Z'"
        )
    instance = instance_of(caregiver, db)
    assert instance["availability_reason"] == "catalog_suspended"


@pytest.mark.parametrize("catalog_profile", ["fixture-active"])
def test_an_uncovered_scenario_creates_one_deduplicated_authoring_request(
    caregiver, db, clock, catalog_profile
) -> None:
    """SPEC 9.8: la solicitud se deduplica por tenant, sujeto, hash y catálogo."""
    with db.write() as connection:
        # Ninguna estrategia calza: el predicate del set exige un valor imposible.
        connection.execute(
            "UPDATE recommendation_set_versions SET applicability_predicate ="
            ' \'{"required_field_values":{"sleep_quality":["restorative"]}}\''
        )
    first = complete_session(caregiver, ids.SUBJECT_ANA)
    clock.advance(hours=25)
    second = complete_session(caregiver, ids.SUBJECT_ANA)
    rows = db.connection.execute(
        "SELECT * FROM authoring_requests WHERE subject_id = ?", (ids.SUBJECT_ANA,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    assert rows[0]["reason"] == "no_approved_match"
    assert first["prediction_episode_id"] != second["prediction_episode_id"]


@pytest.mark.parametrize("catalog_profile", ["fixture-active"])
def test_the_stored_scenario_is_not_readable_as_plain_text(caregiver, db, catalog_profile) -> None:
    """SPEC 9.8: el escenario vive cifrado dentro de la frontera clínica."""
    instance = instance_of(caregiver, db)
    assert b"interrupted" not in bytes(instance["encrypted_scenario"])
    assert b"sleep_quality" not in bytes(instance["encrypted_scenario"])
