"""CLI: `python -m tools.train --db data/blubathon.db --tenant <id>`."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from tools.train.run import TrainingReport, train

DEFAULT_TARGET = "target-demo-fixture-0.3.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.train")
    parser.add_argument("--db", default=Path("data/blubathon.db"), type=Path)
    parser.add_argument("--tenant", default=None)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--dry-run", action="store_true", help="no escribe nada")
    args = parser.parse_args(argv)

    if not args.db.is_file():
        print(f"no existe {args.db}", file=sys.stderr)
        return 2

    connection = sqlite3.connect(args.db)
    try:
        tenant_id = args.tenant or _only_tenant(connection)
        if tenant_id is None:
            print("hay más de un tenant: indique --tenant", file=sys.stderr)
            return 2
        report = train(
            connection,
            tenant_id=tenant_id,
            target_definition_version=args.target,
            dry_run=args.dry_run,
        )
    finally:
        connection.close()

    _print(report, dry_run=args.dry_run)
    return 0 if report.published else 1


def _only_tenant(connection: sqlite3.Connection) -> str | None:
    tenants = [row[0] for row in connection.execute("SELECT tenant_id FROM tenants")]
    return tenants[0] if len(tenants) == 1 else None


def _print(report: TrainingReport, *, dry_run: bool) -> None:
    print(f"episodios usados     {report.n_rows}")
    print(f"  con crisis         {report.n_positive}")
    print(f"  sin crisis         {report.n_negative}")
    print(f"niños                {report.n_subjects}")
    print(f"descartados          {report.skipped_without_baseline} sin tasa base personal")
    print(f"                     {report.skipped_without_predictors} sin ambos predictores")
    print(f"\nestado del run       {report.status}")
    if report.reason:
        print(f"razón                {report.reason}")

    if not report.published:
        print("\nNo se publicó modelo. El intento igual queda registrado.")
        return

    print(f"modelo publicado     {report.model_version} (estado: shadow)")
    print(f"lambda elegido       {report.penalty:g}")
    print(f"\nBrier challenger     {report.brier_challenger:.5f}  (fuera de muestra, LOGO)")
    print(f"Brier baseline       {report.brier_baseline:.5f}  (dentro de muestra)")
    if report.beats_baseline:
        print("El challenger gana pese a que la comparación favorece al baseline.")
    else:
        print("El challenger no gana; con la cancha inclinada a favor del baseline,")
        print("de acá no se concluye que los predictores no sirvan.")

    if report.fit is not None:
        print(
            f"\ncoeficientes         b0={report.fit.intercept:+.4f}"
            f"  sueño={report.fit.beta_sleep:+.2e}"
            f"  regulación={report.fit.beta_regulation:+.2e}"
        )
    if dry_run:
        print("\n(--dry-run: no se escribió nada en la base)")


if __name__ == "__main__":
    raise SystemExit(main())
