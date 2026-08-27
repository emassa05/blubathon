"""La conexión es una sola y la comparten los hilos (SPEC 12.2, CONVENTIONS 13).

`Database` abre SQLite con `check_same_thread=False`, y FastAPI atiende los
endpoints síncronos —y sus `BackgroundTasks`— en un threadpool. Dos hilos, una
conexión: si las transacciones de comando no se serializan, la de uno se lee
como anidamiento del otro y revienta.

La regresión concreta: `GET /v1/outcome-requests` abre escritura porque
rematerializa resoluciones, y chocaba con la redacción en segundo plano que
lanza el envío del formulario. Salía un 500 intermitente.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.api.clock import FrozenClock
from apps.api.settings import Settings
from apps.api.store.db import Database


@pytest.fixture
def database(tmp_path: Path) -> Database:
    settings = Settings(db_path=tmp_path / "concurrencia.db")
    base = Database(settings, clock=FrozenClock(datetime(2026, 8, 26, 12, 0, tzinfo=UTC)))
    base.migrate()
    return base


def test_dos_hilos_escriben_por_turnos(database: Database) -> None:
    """Concurrir hace cola; no revienta."""

    fallos: list[BaseException] = []
    dentro = threading.Barrier(2, timeout=10)

    def escribir() -> None:
        try:
            # Los dos hilos llegan a la vez a la puerta de la transacción: sin
            # el lock, el segundo veía `in_transaction` del primero.
            dentro.wait()
            with database.write() as connection:
                connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
        except BaseException as error:
            fallos.append(error)

    hilos = [threading.Thread(target=escribir) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=15)

    assert not any(hilo.is_alive() for hilo in hilos), "una escritura se quedó bloqueada"
    assert fallos == []


def test_una_lectura_no_se_solapa_con_la_escritura_de_otro_hilo(database: Database) -> None:
    """Leer mientras otro hilo escribe espera su turno en vez de leer a medias."""

    fallos: list[BaseException] = []
    escribiendo = threading.Event()

    def escribir() -> None:
        try:
            with database.write() as connection:
                escribiendo.set()
                connection.execute("SELECT 1").fetchone()
        except BaseException as error:
            fallos.append(error)

    def leer() -> None:
        try:
            escribiendo.wait(timeout=10)
            with database.read() as connection:
                connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
        except BaseException as error:
            fallos.append(error)

    hilos = [threading.Thread(target=escribir), threading.Thread(target=leer)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=15)

    assert not any(hilo.is_alive() for hilo in hilos), "una lectura se quedó bloqueada"
    assert fallos == []


def test_anidar_en_el_mismo_hilo_sigue_siendo_un_error(database: Database) -> None:
    """Serializar entre hilos no puede tapar el error de anidar en uno solo.

    Reentrar es un fallo del programador —dos comandos de dominio en la misma
    unidad de trabajo— y tiene que seguir estallando, no bloquearse contra sí
    mismo esperando un lock que ya tiene.
    """

    with database.write(), pytest.raises(RuntimeError, match="no se anida"), database.write():
        pass
