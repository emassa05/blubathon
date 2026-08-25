"""Salidas por track y sus garantías de contrato (SPEC 8, 11.5).

Cubre INV-18, INV-20 y INV-21 en la frontera de la API.
"""

from __future__ import annotations

from tests.p2.test_episodes_and_outcomes import complete_session
from tools.seed import ids


def outputs_of(caller, episode_id: str) -> dict[str, dict]:
    body = caller.get(f"/api/v1/prediction-episodes/{episode_id}").json()
    return {item["track_id"]: item for item in body["outputs"]}


def test_the_shadow_challenger_is_never_exposed(caregiver, professional, db) -> None:
    """SPEC 8.5: el challenger permanece oculto, también al profesional."""
    result = complete_session(caregiver)
    for caller in (caregiver, professional):
        tracks = outputs_of(caller, result["prediction_episode_id"])
        assert "real_logit_challenger_v1" not in tracks
    stored = db.connection.execute(
        "SELECT track_id, exposed, status, abstention_reasons FROM prediction_outputs"
        " WHERE prediction_episode_id = ? AND track_id = 'real_logit_challenger_v1'",
        (result["prediction_episode_id"],),
    ).fetchone()
    assert stored["exposed"] == 0
    assert stored["status"] == "abstained"
    assert "not_trainable_single_class" in stored["abstention_reasons"]


def test_the_personal_baseline_abstains_with_current_data(caregiver) -> None:
    """INV-20 / SPEC 20.8: menos de 5 outcomes verificados se abstiene."""
    result = complete_session(caregiver)
    baseline = outputs_of(caregiver, result["prediction_episode_id"])["real_personal_baseline_v1"]
    assert baseline["status"] == "abstained"
    assert "insufficient_verified_outcomes" in baseline["abstention_reasons"]
    assert baseline["probability"] is None
    assert baseline["interval"] is None
    assert baseline["interval_method"] is None


def test_an_abstention_carries_no_band_or_decision_policy(caregiver) -> None:
    """INV-21 y SPEC 8.6: v0.3 no tiene bandas ni política de decisión.

    El contrato las declara en el episodio, no por salida: `PredictionOutputView`
    de P1 no tiene dónde poner una banda, y el episodio las fija en `None`.
    """
    result = complete_session(caregiver)
    episode = caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    assert episode["risk_band"] is None
    assert episode["decision_policy_version"] is None
    for output in episode["outputs"]:
        assert "risk_band" not in output
        assert "decision_policy_version" not in output


def test_the_simulation_track_reports_a_score_not_a_probability(caregiver) -> None:
    """SPEC 8.2 y 11.5: score de simulación, sin probabilidad ni intervalo."""
    result = complete_session(caregiver)
    simulation = outputs_of(caregiver, result["prediction_episode_id"])["synthetic_reference_v021"]
    assert simulation["intended_use"] == "simulation_only"
    assert simulation["estimate_kind"] == "simulation_score"
    assert simulation["status"] == "ok"
    assert simulation["simulation_score"] is not None
    assert simulation["probability"] is None
    assert simulation["interval"] is None


def test_the_simulation_track_refuses_a_real_subject(caregiver, db) -> None:
    """INV-18: el modelo sintético rechaza sujetos reales.

    La cohorte se comprueba antes en la autorización; aquí se verifica el propio
    track, sembrando el episodio con la cohorte cambiada después de abrir.
    """
    result = complete_session(caregiver, ids.SUBJECT_BETO)
    with db.write() as connection:
        connection.execute(
            "UPDATE subjects SET cohort_kind = 'real_subject' WHERE subject_id = ?",
            (ids.SUBJECT_BETO,),
        )
        from apps.api.adapters.mock.prediction import MockPrediction

        outputs = MockPrediction().predict(
            tenant_id=ids.TENANT_A,
            subject_id=ids.SUBJECT_BETO,
            prediction_episode_id=result["prediction_episode_id"],
            as_of_at="2026-08-25T12:00:00.000Z",
            cohort_kind="real_subject",
            input_data_origin="real",
            care_mode="home_only",
            target_definition_version=ids.TARGET_DEMO_FIXTURE,
            snapshot={},
        )
    simulation = next(item for item in outputs if item.track_id == "synthetic_reference_v021")
    assert simulation.status == "abstained"
    assert simulation.abstention_reasons == ("real_subject_rejected_by_simulation_track",)


def test_a_synthetic_cohort_marks_its_snapshot_origin(caregiver, db) -> None:
    """SPEC 5.6: origen y cohorte no se mezclan pero sí se corresponden."""
    result = complete_session(caregiver)
    snapshot = db.connection.execute(
        "SELECT input_data_origin FROM feature_snapshots WHERE prediction_episode_id = ?",
        (result["prediction_episode_id"],),
    ).fetchone()
    observations = db.connection.execute(
        "SELECT DISTINCT data_origin FROM field_observations WHERE subject_id = ?",
        (ids.SUBJECT_ANA,),
    ).fetchall()
    assert snapshot["input_data_origin"] == "synthetic"
    assert [row["data_origin"] for row in observations] == ["synthetic"]
