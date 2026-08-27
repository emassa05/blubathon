"""La tabla de frecuencias cuenta bien y no compara celdas que no se pueden leer."""

from __future__ import annotations

from datetime import date

from tools.explore.features import FeatureMatrix
from tools.explore.tables import MIN_DAYS, build_tables


def _matrix(pairs: list[tuple[str, int]], *, subject: str = "s1") -> FeatureMatrix:
    """Una sola columna `x`, una fila por par (valor, desenlace)."""

    return FeatureMatrix(
        columns=("x",),
        rows=tuple((value,) for value, _ in pairs),
        labels=tuple(label for _, label in pairs),
        subjects=tuple(subject for _ in pairs),
        days=tuple(date(2026, 7, 1) for _ in pairs),
        dropped_incomplete=0,
    )


def test_counts_days_and_crises_per_value() -> None:
    matrix = _matrix([("alto", 1), ("alto", 0), ("alto", 0), ("bajo", 0)])

    table = build_tables(matrix).variables[0]
    alto = next(value for value in table.values if value.value == "alto")

    assert (alto.days, alto.crises) == (3, 1)
    assert alto.rate == 1 / 3


def test_a_thin_cell_is_reported_but_not_compared() -> None:
    # `bajo` tiene una tasa altísima con dos días: exactamente la celda que no
    # se puede leer, y la que inflaría el spread si entrara.
    matrix = _matrix(
        [("alto", 0)] * MIN_DAYS + [("medio", 0)] * MIN_DAYS + [("bajo", 1), ("bajo", 1)]
    )

    table = build_tables(matrix).variables[0]
    bajo = next(value for value in table.values if value.value == "bajo")

    assert bajo.rate == 1.0
    assert not bajo.is_comparable
    assert table.spread == 0.0


def test_spread_is_none_without_two_readable_values() -> None:
    matrix = _matrix([("alto", 0)] * MIN_DAYS + [("bajo", 1)])

    assert build_tables(matrix).variables[0].spread is None


def test_counts_how_many_children_contributed_each_value() -> None:
    matrix = FeatureMatrix(
        columns=("x",),
        rows=(("alto",), ("alto",), ("bajo",)),
        labels=(0, 0, 0),
        subjects=("s1", "s2", "s1"),
        days=tuple(date(2026, 7, 1) for _ in range(3)),
        dropped_incomplete=0,
    )

    table = build_tables(matrix).variables[0]

    assert next(value for value in table.values if value.value == "alto").subjects == 2
    assert next(value for value in table.values if value.value == "bajo").subjects == 1


def test_variables_without_comparable_values_sort_last() -> None:
    matrix = FeatureMatrix(
        columns=("legible", "escasa"),
        rows=tuple(
            ("alto" if index < MIN_DAYS else "bajo", f"v{index}") for index in range(2 * MIN_DAYS)
        ),
        labels=tuple(0 for _ in range(2 * MIN_DAYS)),
        subjects=tuple("s1" for _ in range(2 * MIN_DAYS)),
        days=tuple(date(2026, 7, 1) for _ in range(2 * MIN_DAYS)),
        dropped_incomplete=0,
    )

    report = build_tables(matrix)

    assert [variable.name for variable in report.variables] == ["legible", "escasa"]
    assert report.variables[1].spread is None
