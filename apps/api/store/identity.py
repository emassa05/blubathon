"""Consultas de identidad, sujetos y perfiles (SPEC 5.7, 13)."""

from __future__ import annotations

import sqlite3
from typing import Any

from apps.api.store.json_columns import load_list
from apps.api.store.projection import project_as_of


def subject(connection: sqlite3.Connection, subject_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT subject_id, tenant_id, display_label, cohort_kind, created_at"
        " FROM subjects WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()


def subjects_for_tenant(connection: sqlite3.Connection, *, tenant_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT subject_id, tenant_id, display_label, cohort_kind FROM subjects"
        " WHERE tenant_id = ? ORDER BY display_label",
        (tenant_id,),
    ).fetchall()


def active_profile(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_id: str,
    cutoff: str,
) -> dict[str, Any] | None:
    """Hoja vigente del perfil al cutoff. Sin perfil no hay escenario (SPEC 9.7)."""
    rows = connection.execute(
        "SELECT * FROM subject_profiles WHERE tenant_id = ? AND subject_id = ?"
        " AND effective_from <= ?",
        (tenant_id, subject_id, cutoff),
    ).fetchall()
    projection = project_as_of(
        (dict(row) for row in rows),
        cutoff,
        id_field="subject_profile_id",
        effective_field="effective_from",
    )
    if projection.has_invalid_chain or not projection.leaves:
        return None
    leaf = projection.leaves[-1]
    return {
        "subject_profile_id": leaf["subject_profile_id"],
        "profile_version": leaf["profile_version"],
        "care_mode": leaf["care_mode"],
        "sensory_profile_tags": load_list(leaf["sensory_profile_tags"]),
        "communication_support_tags": load_list(leaf["communication_support_tags"]),
        "contraindication_tags": load_list(leaf["contraindication_tags"]),
    }


def target_definition(
    connection: sqlite3.Connection, target_definition_version: str
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM target_definition_versions WHERE target_definition_version = ?",
        (target_definition_version,),
    ).fetchone()


def select_target_definition(
    connection: sqlite3.Connection,
    *,
    scope: str,
    tenant_id: str | None,
    cutoff: str,
) -> tuple[sqlite3.Row | None, str]:
    """SPEC 4.3: exactamente una activa efectiva, o fail-closed.

    Devuelve ``(fila, razón)`` donde la razón es ``available``,
    ``target_definition_unavailable`` o ``target_definition_ambiguous``.
    """
    rows = connection.execute(
        "SELECT * FROM target_definition_versions"
        " WHERE scope = ? AND COALESCE(tenant_id, '') = COALESCE(?, '')"
        " AND approval_status = 'active'"
        " AND effective_from <= ?"
        " AND (retired_at IS NULL OR retired_at > ?)"
        " ORDER BY effective_from DESC, target_definition_version",
        (scope, tenant_id, cutoff, cutoff),
    ).fetchall()
    if not rows:
        return None, "target_definition_unavailable"
    if len(rows) > 1:
        return None, "target_definition_ambiguous"
    return rows[0], "available"
