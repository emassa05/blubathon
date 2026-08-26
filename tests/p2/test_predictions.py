"""Prediction output guarantees retained by v0.4."""

from __future__ import annotations

from tests.p2.conftest import submit_form


def test_abstained_outputs_expose_no_numeric_estimate(client) -> None:
    submitted = submit_form(client).json()
    episode = client.get(f"/v1/prediction-episodes/{submitted['prediction_episode_id']}").json()
    for output in episode["outputs"]:
        if output["status"] == "ok":
            continue
        assert output["probability"] is None
        assert output["simulation_score"] is None
        assert output["interval"] is None
        assert output["abstention_reasons"]


def test_simulation_track_is_not_a_clinical_probability(client) -> None:
    submitted = submit_form(client).json()
    episode = client.get(f"/v1/prediction-episodes/{submitted['prediction_episode_id']}").json()
    simulation = next(
        output for output in episode["outputs"] if output["track_id"] == "synthetic_reference_v021"
    )
    assert simulation["intended_use"] == "simulation_only"
    assert simulation["simulation_score"] is not None
    assert simulation["probability"] is None
