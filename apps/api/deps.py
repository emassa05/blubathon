"""Dependencias compartidas de FastAPI — conexión a SQLite por request."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from apps.api.store.db import DEFAULT_DB_PATH, get_connection, init_db


def get_db() -> Iterator[sqlite3.Connection]:
    conn = get_connection(DEFAULT_DB_PATH)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()
