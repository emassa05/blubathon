"""El camino real existe y respeta los mismos invariantes que el mock.

`FARO_P1_ADAPTERS` elige el conjunto. Estos tests corren en los dos y afirman lo
que no depende del conjunto: qué adaptadores quedaron cableados, y que ninguna
salida rompe SPEC 8.5 ni SPEC 11.5 venga de donde venga.
"""

from __future__ import annotations

import os

import pytest

from apps.api.adapters import build_ports
from apps.api.adapters.mock import MOCK_SOURCE
from apps.api.adapters.p1 import MISSING_FACADES, REAL_SOURCE, P1FacadesUnavailable
from apps.api.store.db import Database
from tests.p2.test_episodes_and_outcomes import complete_session
from tools.seed import ids

SELECTED = os.environ.get("FARO_P1_ADAPTERS", "mock")


def test_every_declared_facade_is_wired() -> None:
    """Nada queda declarado como façade faltante: todas están cableadas."""
    assert MISSING_FACADES == ()


def test_the_real_set_refuses_to_run_without_a_database() -> None:
    """El dominio de P1 es puro sobre filas ya cargadas; quien las carga es el
    adaptador. Sin base falla explícito en vez de fingir un resultado."""
    with pytest.raises(P1FacadesUnavailable):
        build_ports("real", database=None)


def test_the_selected_set_is_the_one_the_environment_asked_for(app) -> None:
    expected = REAL_SOURCE if SELECTED == "real" else MOCK_SOURCE
    assert app.state.registry.core.ports.source == expected


def test_the_real_set_wires_the_published_domain(settings, clock) -> None:
    """Cada puerto queda cableado a `apps/api/adapters/p1`, sin `FARO_P1_ADAPTERS`.

    Se construye explícitamente para que la afirmación no dependa de qué
    conjunto eligió el entorno de esta corrida.
    """
    database = Database(settings, clock=clock)
    try:
        ports = build_ports("real", database=database)
        assert ports.source == REAL_SOURCE
        for port in (ports.defaults, ports.form, ports.prediction, ports.rag):
            assert type(port).__module__.startswith("apps.api.adapters.p1")
    finally:
        database.close()


def test_no_output_carries_a_number_without_a_status_that_allows_it(caregiver) -> None:
    """SPEC 8.5 y 11.5, en cualquier conjunto de adaptadores."""
    result = complete_session(caregiver, ids.SUBJECT_ANA)
    episode = caregiver.get(f"/api/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    tracks = {output["track_id"]: output for output in episode["outputs"]}

    # SPEC 8.5: el challenger en sombra nunca se expone.
    assert "real_logit_challenger_v1" not in tracks

    for output in episode["outputs"]:
        if output["status"] == "ok":
            continue
        assert output["probability"] is None
        assert output["simulation_score"] is None
        assert output["interval"] is None
        assert output["interval_method"] is None
        assert output["abstention_reasons"]

    simulation = tracks["synthetic_reference_v021"]
    # SPEC 8.2: una simulación nunca se presenta como probabilidad clínica.
    assert simulation["intended_use"] == "simulation_only"
    assert simulation["probability"] is None
