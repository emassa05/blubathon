"""Persistencia del volante y lectura de reportes de evaluación (SPEC 10.5, 14).

La API importa manifests que produce `tools/train`; no entrena aquí dentro.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from apps.api.store.json_columns import load_list


def published_report(
    connection: sqlite3.Connection, *, tenant_id: str, model_version: str
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT r.*, m.track_id, m.training_data_origin, m.state, m.intended_use"
        " FROM evaluation_reports AS r"
        " JOIN model_versions AS m ON m.model_version = r.model_version"
        " WHERE r.tenant_id = ? AND r.model_version = ? AND r.status = 'published'"
        " ORDER BY r.published_at DESC LIMIT 1",
        (tenant_id, model_version),
    ).fetchone()
    if row is None:
        return None
    return dict(row) | {
        "metrics": load_list(row["metrics"]),
        "abstentions": load_list(row["abstentions"]),
    }
