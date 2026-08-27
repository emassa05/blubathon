"""CLI: `python -m tools.demo` deja la base lista para probar todo."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from apps.api.canonical import canonical_timestamp
from apps.api.settings import load_settings
from apps.api.store.db import connect
from apps.api.store.migrations import migrate
from tools.demo.montaje import DIAS_POR_DEFECTO, montar_demo


def _borrar(ruta: Path) -> bool:
    """Borra la base y sus archivos WAL. `False` si algo la tiene abierta.

    En Windows no se puede borrar un archivo que otro proceso tiene abierto, y
    el que la tiene abierta casi siempre es la API. Sin este aviso el fallo sale
    como un `WinError 32` a media traza y es fácil leerlo como que la semilla
    está rota, cuando lo único que hace falta es parar el servidor.
    """

    for sufijo in ("", "-shm", "-wal"):
        objetivo = Path(str(ruta) + sufijo)
        try:
            objetivo.unlink(missing_ok=True)
        except PermissionError:
            print(f"no se puede borrar {objetivo}: otro proceso la tiene abierta.")
            print("Pará la API y volvé a correr esto:")
            print("  taskkill /F /IM python.exe     (o Ctrl+C en la consola de uvicorn)")
            print()
            print("Sin --reset, la semilla escribe sobre lo que ya hay y duplica días.")
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.demo",
        description="Siembra, fabrica historial y entrena: la base queda lista para probar",
    )
    parser.add_argument("--db", type=Path, help="ruta de la base; por defecto la de settings")
    parser.add_argument(
        "--dias",
        type=int,
        default=DIAS_POR_DEFECTO,
        help=f"días de historial por niño (por defecto {DIAS_POR_DEFECTO})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="borra la base antes de sembrar; sin esto, sembrar dos veces duplica días",
    )
    args = parser.parse_args(argv)

    # `tools.demo_history` abre su propia conexión leyendo el entorno, así que
    # la ruta se fija aquí para que todos los pasos miren la misma base.
    if args.db:
        os.environ["BLUBATHON_DB_PATH"] = str(args.db)
    ruta = Path(load_settings().db_path)

    if args.reset and not _borrar(ruta):
        return 1

    connection = connect(ruta)
    try:
        migrate(connection, canonical_timestamp(datetime.now(UTC)))
        resultado = montar_demo(connection, dias=args.dias)
    finally:
        connection.close()

    print()
    print(f"base                 {ruta}")
    print(f"corpus               {resultado.fragmentos} fragmentos indexados")
    for nino in resultado.ninos:
        print(f"{nino.etiqueta:20s} {nino.dias} días, {nino.verificados} resultados verificados")
        print(f"                     {nino.child_id}")
    if resultado.entrenado:
        print(f"modelo               {resultado.modelo}")
    else:
        print(f"modelo               NO se publicó ({resultado.motivo_sin_modelo})")
    print()
    print("Arrancá la API con adaptadores reales, o el riesgo se abstiene igual:")
    print(
        '  BLUBATHON_P1_ADAPTERS=real python -m uvicorn "apps.api.main:create_app"'
        " --factory --port 8000"
    )
    print()
    print("La redacción de la recomendación necesita además un modelo de lenguaje:")
    print("  BLUBATHON_DRAFT_LLM=ollama   (o anthropic, con ANTHROPIC_API_KEY)")
    print("Sin él, la recuperación funciona y la redacción abstiene con draft_unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
