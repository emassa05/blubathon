"""`python -m tools.seed` siembra la base local de demostración."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from apps.api.settings import load_settings
from apps.api.store.db import Database
from tools.seed.seeder import seed, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra la demo local de Blubathon")
    parser.add_argument(
        "--catalog",
        choices=("blocked", "fixture-active"),
        default="blocked",
        help=(
            "blocked: sin revisor clínico autorizado, el runtime abstiene con "
            "clinical_review_unavailable. fixture-active: catálogo ficticio "
            "activado para recorrer el flujo profesional."
        ),
    )
    parser.add_argument("--db", type=Path, default=None, help="Ruta de la base SQLite")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.db is not None:
        # `Settings` es un dataclass con `slots=True`, así que no tiene `__dict__`.
        # `replace` es la forma de derivar una copia con un campo cambiado.
        settings = replace(settings, db_path=args.db)
    database = Database(settings)
    database.migrate()
    with database.write() as connection:
        result = seed(connection, catalog_profile=args.catalog)
    database.close()
    print(json.dumps(summary(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
