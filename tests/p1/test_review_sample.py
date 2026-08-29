"""El sorteo que decide qué recomendación llega a revisión profesional."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from packages.shared.constants import REVIEW_SAMPLE_DENOMINATOR
from packages.shared.domain.review import is_in_review_sample


def test_the_draw_is_stable_for_the_same_identifier() -> None:
    """Sin esto la cola sería otra en cada recarga y el elemento que se está
    leyendo desaparecería al refrescar."""

    identifier = uuid4()
    assert is_in_review_sample(identifier) == is_in_review_sample(identifier)


def test_the_draw_does_not_depend_on_how_the_identifier_is_spelled() -> None:
    identifier = uuid4()
    assert is_in_review_sample(identifier) is is_in_review_sample(UUID(str(identifier)))


def test_about_one_in_the_denominator_is_selected() -> None:
    """Una muestra que no muestrea no es una muestra: si el corte dejara pasar
    todo, el profesional volvería a tener delante el trabajo entero."""

    draws = 4000
    selected = sum(is_in_review_sample(uuid4()) for _ in range(draws))
    expected = draws / REVIEW_SAMPLE_DENOMINATOR
    # Holgura amplia a propósito: se comprueba el orden de magnitud del corte,
    # no la calidad estadística de SHA-256, y un test que falla una vez cada
    # tantas ejecuciones es peor que no tenerlo.
    assert expected * 0.75 <= selected <= expected * 1.25


# Sorteo fijado a mano contra la política vigente. Cambiar el algoritmo o
# `REVIEW_SAMPLE_POLICY_VERSION` hace fallar este test, que es justamente lo que
# tiene que pasar: rebarajar la cola es una decisión, y sin este pin ocurriría
# de callado y nadie podría reconstruir por qué se revisó una y no otra.
PINNED = (
    ("00000000-0000-4000-8000-000000000001", True),
    ("00000000-0000-4000-8000-000000000002", False),
    ("00000000-0000-4000-8000-000000000003", False),
    ("00000000-0000-4000-8000-000000000004", True),
    ("00000000-0000-4000-8000-000000000005", False),
    ("00000000-0000-4000-8000-000000000006", False),
    ("00000000-0000-4000-8000-000000000007", False),
    ("00000000-0000-4000-8000-000000000008", True),
)


@pytest.mark.parametrize(("identifier", "expected"), PINNED)
def test_the_selection_is_reproducible_across_processes(identifier: str, expected: bool) -> None:
    assert is_in_review_sample(UUID(identifier)) is expected
