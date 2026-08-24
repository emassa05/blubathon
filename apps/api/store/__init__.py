"""SQLite persistence for daily logs and feedback (SPEC 1, 2.5)."""

from apps.api.store.db import DEFAULT_DB_PATH, get_connection, init_db
from apps.api.store.repository import (
    get_history,
    insert_feedback,
    insert_log,
    insert_logs,
    latest_date,
    list_child_ids,
)

# seed is intentionally not re-exported: importing it here makes
# `python -m apps.api.store.seed` warn, because runpy would find the module
# already in sys.modules. Import it directly where it is needed.

__all__ = [
    "DEFAULT_DB_PATH",
    "get_connection",
    "get_history",
    "init_db",
    "insert_feedback",
    "insert_log",
    "insert_logs",
    "latest_date",
    "list_child_ids",
]
