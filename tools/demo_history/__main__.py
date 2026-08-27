"""CLI: `python -m tools.demo_history --child <uuid> --days 8 --positives 3`."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from apps.api.settings import load_settings
from tools.demo_history.builder import build_history


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Siembra días cerrados con su resultado ya verificado",
    )
    parser.add_argument("--child", required=True, help="child_id del sujeto")
    parser.add_argument(
        "--days",
        type=int,
        default=8,
        help="días cerrados a sembrar, contando desde ayer hacia atrás (por defecto 8)",
    )
    parser.add_argument(
        "--dificiles",
        type=int,
        default=3,
        help=(
            "cuántos de esos días vienen con mal perfil (por defecto 3). "
            "Si hubo crisis lo decide un sorteo reproducible, no el perfil"
        ),
    )
    parser.add_argument(
        "--perfil",
        choices=("mixto", "sueno"),
        default="mixto",
        help=(
            "que campos vienen mal en un dia dificil. mixto: sueno, digestivo, "
            "medicacion y regulacion a la vez. sueno: solo el sueno, el resto "
            "bien, para que la recomendacion salga sobre sueno"
        ),
    )
    parser.add_argument("--db", help="ruta de la base SQLite")
    parser.add_argument(
        "--adapters",
        choices=("mock", "real"),
        help="conjunto de adaptadores; por defecto el de BLUBATHON_P1_ADAPTERS",
    )
    args = parser.parse_args()

    if args.db:
        os.environ["BLUBATHON_DB_PATH"] = str(Path(args.db))

    result = build_history(
        child_id=args.child,
        days=args.days,
        dificiles=args.dificiles,
        perfil=args.perfil,
        settings=load_settings(),
        adapters=args.adapters,
    )
    print(
        json.dumps(
            {
                "child_id": result.child_id,
                "verified_outcomes": result.verified,
                "days": [asdict(day) for day in result.days],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
