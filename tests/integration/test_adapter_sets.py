"""El camino real existe y respeta los mismos invariantes que el mock.

`BLUBATHON_P1_ADAPTERS` elige el conjunto. Estos tests corren en los dos y afirman lo
que no depende del conjunto: qué adaptadores quedaron cableados, y que ninguna
salida rompe los invariantes venga de donde venga.
"""

from __future__ import annotations

import os

import pytest

from apps.api.adapters import build_ports
from apps.api.adapters.mock import MOCK_SOURCE
from apps.api.adapters.p1 import MISSING_FACADES, REAL_SOURCE, P1FacadesUnavailable
from apps.api.store.db import Database
from tests.p2.conftest import submit_form
from tools.seed import ids

SELECTED = os.environ.get("BLUBATHON_P1_ADAPTERS", "mock")


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
    """Cada puerto queda cableado a `apps/api/adapters/p1`, sin `BLUBATHON_P1_ADAPTERS`.

    Se construye explícitamente para que la afirmación no dependa de qué
    conjunto eligió el entorno de esta corrida.
    """
    database = Database(settings, clock=clock)
    try:
        ports = build_ports("real", database=database)
        assert ports.source == REAL_SOURCE
        for port in (ports.defaults, ports.form, ports.prediction):
            assert type(port).__module__.startswith("apps.api.adapters.p1")
    finally:
        database.close()


def test_no_output_carries_a_number_without_a_status_that_allows_it(caregiver) -> None:
    """En cualquier conjunto de adaptadores."""
    result = submit_form(caregiver, str(ids.SUBJECT_ANA)).json()
    episode = caregiver.get(f"/v1/prediction-episodes/{result['prediction_episode_id']}").json()
    tracks = {output["track_id"]: output for output in episode["outputs"]}

    # El challenger ya es operativo, pero solo aparece donde hay modelo: el
    # conjunto `mock` no entrena nada, así que ahí sigue sin salir.
    challenger = tracks.get("real_logit_challenger_v1")
    if challenger is not None:
        assert challenger["intended_use"] == "operational_support"
        # Sin intervalo: una estimación puntual no publica incertidumbre propia.
        assert challenger["interval"] is None

    for output in episode["outputs"]:
        if output["status"] == "ok":
            continue
        assert output["probability"] is None
        assert output["simulation_score"] is None
        assert output["interval"] is None
        assert output["interval_method"] is None
        assert output["abstention_reasons"]

    simulation = tracks["synthetic_reference_v021"]
    assert simulation["intended_use"] == "simulation_only"
    assert simulation["probability"] is None
