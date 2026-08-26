"""CLI: `python -m tools.explore [--db data/blubathon.db] [--seeds 20]`."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from tools.explore.features import build_matrix
from tools.explore.forest import importance_stability


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.explore")
    parser.add_argument("--db", default=Path("data/blubathon.db"), type=Path)
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
        print("sin episodios resueltos: nada que explorar", file=sys.stderr)
        return 1
    if matrix.positives < 2:
        print(
            f"sólo {matrix.positives} desenlace(s) positivo(s): un bosque no dice nada acá",
            file=sys.stderr,
        )
        return 1

    print(f"filas                {len(matrix.labels)}")
    print(f"  con crisis         {matrix.positives}")
    print(f"  sin crisis         {matrix.negatives}")
    print(f"prevalencia          {matrix.prevalence:.1%}")
    print(f"descartadas          {matrix.dropped_incomplete} filas (variables faltantes)")
    for name, coverage in matrix.dropped_columns:
        print(f"  columna fuera      {name} (presente en {coverage:.0%} de los días)")
    for name in matrix.constant_columns:
        print(f"  columna fuera      {name} (no varía dentro de ningún sujeto)")
    print(f"semillas             {args.seeds}\n")

    report = importance_stability(matrix, seeds=args.seeds, trees=args.trees)

    header = (
        f"{'variable':28} {'puesto medio':>13} {'1º de ' + str(args.seeds):>9}"
        f" {'rango':>7} {'importancia':>12}"
    )
    print(header)
    print("-" * len(header))
    for variable in report.variables:
        print(
            f"{variable.name:28} {variable.mean_rank:>13.1f}"
            f" {variable.times_first:>9} {variable.rank_span:>7}"
            f" {variable.mean_importance:>+12.4f}"
        )

    print(
        f"\nUn modelo que dijera siempre «no hay crisis» acertaría"
        f" {report.majority_class_accuracy:.1%}."
    )
    if report.none_helps:
        print(
            "Ninguna variable tiene importancia positiva fuera de muestra: incluirlas"
            " empeora la predicción sobre un sujeto no visto. El orden de arriba dice"
            " cuál perjudica menos, no cuál predice mejor."
        )
    if report.is_stable:
        winner = next(v for v in report.variables if v.times_first == report.seeds)
        print(f"El primer puesto es estable: {winner.name} gana en las {report.seeds} semillas.")
    else:
        disputed = [v.name for v in report.variables if v.times_first > 0]
        print(
            f"El primer puesto NO es estable: se lo disputan {', '.join(disputed)}"
            f" según la semilla. Con {report.n_positive} eventos el orden es ruido;"
            " la dirección del efecto es lo único que el dato sostiene."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
