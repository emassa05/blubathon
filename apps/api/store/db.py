"""Conexión SQLite de la demo y unidad de trabajo (SPEC 12.3, CONVENTIONS 13).

Todo el SQL del proyecto vive bajo `apps/api/store`. No se ejecuta DDL por
request: el runner de migraciones corre al arrancar o desde `tools.seed`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from apps.api.canonical import canonical_timestamp
from apps.api.clock import Clock, system_clock
from apps.api.settings import Settings
from apps.api.store.migrations import migrate

BUSY_TIMEOUT_MS = 5000


def connect(db_path: Path | str, *, read_only: bool = False) -> sqlite3.Connection:
    """Abre la base con FK activas, WAL y `busy_timeout` (CONVENTIONS 13)."""
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
        """Una transacción por comando de dominio (SPEC 12.2).

        `BEGIN IMMEDIATE` toma el lock de escritura al entrar: es lo que serializa
        la decisión de oportunidad canónica por `(tenant_id, subject_id)` en la
        demo SQLite (SPEC 4.2). En piloto el equivalente es `SELECT ... FOR UPDATE`
        sobre la fila del sujeto.
        """
        if self._connection.in_transaction:
            raise RuntimeError("una transacción de comando no se anida")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        self._connection.commit()

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """Lectura consistente sin tomar el lock de escritura."""
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
