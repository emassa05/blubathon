"""CLI: `python -m tools.explore [--db data/blubathon.db]`.

Por defecto cuenta. `--bosque` corre además el bosque aleatorio, que responde la
misma pregunta con un método que no se explica en una frase.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from tools.explore.features import build_matrix
from tools.explore.tables import MIN_DAYS, FrequencyReport, build_tables


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.explore")
    parser.add_argument("--db", default=Path("data/blubathon.db"), type=Path)
    parser.add_argument("--bosque", action="store_true", help="además, bosque aleatorio")
    parser.add_argument("--seeds", default=20, type=int)
    parser.add_argument("--trees", default=500, type=int)
    args = parser.parse_args(argv)

    if not args.db.is_file():
        print(f"no existe {args.db}", file=sys.stderr)
        return 2

    connection = sqlite3.connect(args.db)
    try:
        matrix = build_matrix(connection)
    finally:
        connection.close()

    if not matrix.labels:
        print("sin episodios resueltos: nada que contar", file=sys.stderr)
        return 1

    print(f"días con desenlace   {len(matrix.labels)}")
    print(f"  con crisis         {matrix.positives}")
    print(f"  sin crisis         {matrix.negatives}")
    print(f"tasa base            {matrix.prevalence:.1%}")
    for name, coverage in matrix.dropped_columns:
        print(f"  variable fuera     {name} (registrada sólo el {coverage:.0%} de los días)")
    for name in matrix.constant_columns:
        print(f"  variable fuera     {name} (nunca cambia dentro de un mismo niño)")
    print()

    _print_tables(build_tables(matrix))

    if args.bosque:
        _print_forest(matrix, seeds=args.seeds, trees=args.trees)
    return 0


def _print_tables(report: FrequencyReport) -> None:
    print(f"{'':38} {'días':>6} {'crisis':>7} {'tasa':>8} {'niños':>6}")
    for variable in report.variables:
        print(variable.name)
        for value in variable.values:
            marca = " " if value.is_comparable else "*"
            print(
                f"  {value.value:36} {value.days:>6} {value.crises:>7}"
                f" {value.rate:>7.1%}{marca} {value.subjects:>6}"
            )
        if variable.spread is not None:
            puntos = variable.spread * 100
            print(f"  la tasa se mueve {puntos:.1f} puntos entre los valores comparables")
        else:
            print("  ningún par de valores tiene días suficientes para compararse")
        print()

    print(
        f"* menos de {MIN_DAYS} días: con una tasa base del {report.prevalence:.1%} esa celda"
        f" espera menos de una crisis, así que su porcentaje no mide nada."
    )
    print(
        f"Los {report.n_positive} eventos se reparten entre niños con tasas base distintas;"
        " una tasa alta puede venir del niño y no de la variable."
    )
    print(
        "Esto es asociación en los datos que ya tenemos, no capacidad de predecir a un niño"
        " nuevo: es el punto de partida del modelo, no su validación."
    )
    if not report.any_comparable:
        print("Ninguna variable tiene dos valores con días suficientes para compararse.")


def _print_forest(matrix, *, seeds: int, trees: int) -> None:
    from tools.explore.forest import importance_stability

    if matrix.positives < 2:
        print("\nbosque: hacen falta al menos dos crisis", file=sys.stderr)
        return

    report = importance_stability(matrix, seeds=seeds, trees=trees)
    header = f"\n{'variable':28} {'puesto medio':>13} {'1º de ' + str(seeds):>9} {'rango':>7}"
    print(header)
    print("-" * (len(header) - 1))
    for variable in report.variables:
        print(
            f"{variable.name:28} {variable.mean_rank:>13.1f}"
            f" {variable.times_first:>9} {variable.rank_span:>7}"
        )
    if report.none_helps:
        print(
            "Ninguna variable tiene importancia positiva fuera de muestra: el orden dice"
            " cuál perjudica menos, no cuál predice mejor."
        )


if __name__ == "__main__":
    raise SystemExit(main())
