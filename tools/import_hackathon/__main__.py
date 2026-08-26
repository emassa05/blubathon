"""CLI: `python -m tools.import_hackathon --dir <carpeta> [--db data/blubathon.db]`."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from tools.import_hackathon.importer import import_from_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.import_hackathon")
    parser.add_argument("--dir", required=True, type=Path, help="carpeta con los cinco CSV")
    parser.add_argument("--db", default=Path("data/blubathon.db"), type=Path)
    parser.add_argument(
        "--dry-run", action="store_true", help="lee y valida, revierte antes de confirmar"
    )
    args = parser.parse_args(argv)

    if not args.db.is_file():
        print(f"no existe {args.db}; corré `python -m tools.seed` primero", file=sys.stderr)
        return 2

    connection = sqlite3.connect(args.db)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            report = import_from_directory(connection, args.dir)
            if args.dry_run:
                connection.rollback()
    finally:
        connection.close()

    print(f"sujetos              {report.subjects}")
    print(f"observaciones        {report.observations}")
    print(f"sesiones terapia     {report.sessions_imported}")
    print(f"episodios            {report.episodes}")
    print(f"  desenlace sí       {report.positives}")
    print(f"  desenlace no       {report.negatives}")
    print(f"prevalencia          {report.prevalence:.1%}")
    if report.unmatched_events:
        print(f"eventos sin episodio {', '.join(report.unmatched_events)}")
    if args.dry_run:
        print("\n(dry-run: nada se escribió)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
