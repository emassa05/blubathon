"""Migraciones inmutables con número, nombre y checksum (CONVENTIONS 13).

Una migración publicada no se modifica: se crea otra. El runner verifica el
checksum de lo aplicado y falla si un archivo cambió.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent
_FILENAME = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")

BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    number      INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL
);
"""


class MigrationError(RuntimeError):
    """Una migración cambió después de publicarse, o falta un archivo aplicado."""


@dataclass(frozen=True, slots=True)
class Migration:
    number: int
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


def discover(directory: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    found: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = _FILENAME.match(path.name)
        if match is None:
            raise MigrationError(f"nombre de migración inválido: {path.name}")
        found.append(
            Migration(int(match.group(1)), match.group(2), path.read_text(encoding="utf-8"))
        )
    numbers = [migration.number for migration in found]
    if numbers != sorted(set(numbers)):
        raise MigrationError("números de migración duplicados o desordenados")
    return tuple(found)


def applied(connection: sqlite3.Connection) -> dict[int, tuple[str, str]]:
    connection.executescript(BOOKKEEPING)
    rows = connection.execute(
        "SELECT number, name, checksum FROM schema_migrations ORDER BY number"
    ).fetchall()
    return {row["number"]: (row["name"], row["checksum"]) for row in rows}


def migrate(connection: sqlite3.Connection, now: str, *, directory: Path = MIGRATIONS_DIR) -> int:
    """Aplica las migraciones pendientes. Devuelve cuántas se aplicaron."""
    known = applied(connection)
    pending = 0
    for migration in discover(directory):
        record = known.get(migration.number)
        if record is not None:
            if record[1] != migration.checksum:
                raise MigrationError(
                    f"la migración {migration.number:03d}_{migration.name} cambió "
                    "después de aplicarse; crea otra en su lugar"
                )
            continue
        # Cada migración corre completa o no corre: DDL dentro de una transacción.
        connection.execute("BEGIN")
        try:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(number, name, checksum, applied_at)"
                " VALUES (?, ?, ?, ?)",
                (migration.number, migration.name, migration.checksum, now),
            )
        except Exception:
            connection.rollback()
            raise
        connection.commit()
        pending += 1
    return pending
