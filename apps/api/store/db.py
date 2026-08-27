"""Conexión SQLite de la demo y unidad de trabajo.

Todo el SQL del proyecto vive bajo `apps/api/store`. No se ejecuta DDL por
request: el runner de migraciones corre al arrancar o desde `tools.seed`.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from apps.api.canonical import canonical_timestamp
from apps.api.clock import Clock, system_clock
from apps.api.settings import Settings
from apps.api.store.migrations import migrate

BUSY_TIMEOUT_MS = 5000


def connect(db_path: Path | str, *, read_only: bool = False) -> sqlite3.Connection:
    """Abre la base con FK activas, WAL y `busy_timeout`."""
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if str(path) != ":memory:":
        connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    if read_only:
        connection.execute("PRAGMA query_only = ON")
    return connection


class Database:
    """Dueña de la conexión y de las transacciones de comando."""

    def __init__(self, settings: Settings, *, clock: Clock = system_clock) -> None:
        settings.validate()
        self._settings = settings
        self._clock = clock
        self._connection = connect(settings.db_path)
        # La conexión es una sola y se comparte entre hilos
        # (`check_same_thread=False`): las peticiones síncronas de FastAPI y sus
        # `BackgroundTasks` corren en el threadpool. Sin serializar, dos hilos
        # se pisan las fronteras de transacción del otro.
        self._transaction_lock = threading.RLock()
        # Qué hilo tiene abierta la transacción de comando, para distinguir
        # anidar (error del programador) de concurrir (esperar el turno).
        self._writer: int | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    @property
    def settings(self) -> Settings:
        return self._settings

    def migrate(self) -> int:
        return migrate(self._connection, canonical_timestamp(self._clock()))

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """Una transacción por comando de dominio.

        `BEGIN IMMEDIATE` toma el lock de escritura al entrar: es lo que serializa
        la decisión de oportunidad canónica por `(tenant_id, subject_id)` en la
        demo SQLite. En piloto el equivalente es `SELECT... FOR UPDATE`
        sobre la fila del sujeto.

        Concurrir no es anidar. Con una sola conexión compartida entre hilos,
        mirar `in_transaction` confundía las dos cosas: la transacción de otro
        hilo se leía como anidamiento y reventaba en vez de esperar su turno.
        Los tramos son cortos —el LLM y la recuperación quedan fuera— así que
        hacer cola aquí no bloquea nada de forma apreciable.
        """
        if self._writer == threading.get_ident():
            raise RuntimeError("una transacción de comando no se anida")
        # Se comprueba el anidamiento **antes** de tomar el lock: reentrar en el
        # mismo hilo tiene que fallar, no bloquearse contra sí mismo.
        with self._transaction_lock:
            self._writer = threading.get_ident()
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except Exception:
                self._connection.rollback()
                raise
            finally:
                self._writer = None
            self._connection.commit()

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """Lectura consistente sin tomar el lock de escritura de SQLite.

        Sí toma el del proceso: la conexión es una y compartida, así que una
        lectura no puede solaparse con la transacción de otro hilo sin leer
        estado a medio escribir.
        """
        with self._transaction_lock:
            # Dentro de una transacción ya abierta —una lectura dentro de un
            # comando, en este mismo hilo— se lee de ella y no se cierra nada:
            # cerrarla desharía el comando a medias.
            if self._connection.in_transaction:
                yield self._connection
                return
            self._connection.execute("BEGIN")
            try:
                yield self._connection
            finally:
                self._connection.rollback()

    def close(self) -> None:
        self._connection.close()
