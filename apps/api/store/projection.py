"""`project_as_of` sobre cadenas append-only.

Una lectura estadística nunca ve una corrección posterior al cutoff. Ramas,
ciclos y referencias cross-tenant invalidan la cadena completa en vez de
resolverse "por conveniencia": el resultado las reporta aparte para que el
llamador se abstenga.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Projection:
    """Hojas vigentes al cutoff y cadenas que quedaron inválidas."""

    leaves: tuple[dict[str, Any], ...]
    invalid_ids: frozenset[str]

    @property
    def has_invalid_chain(self) -> bool:
        return bool(self.invalid_ids)


def project_as_of(
    rows: Iterable[Mapping[str, Any]],
    cutoff: str,
    *,
    id_field: str,
    supersedes_field: str = "supersedes_id",
    ingested_field: str = "ingested_at",
    effective_field: str | None = None,
    tenant_field: str = "tenant_id",
) -> Projection:
    """Conserva la hoja vigente de cada cadena conocida al cutoff."""
    kept: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        if row[ingested_field] > cutoff:
            continue
        if (
            effective_field is not None
            and row.get(effective_field) is not None
            and row[effective_field] > cutoff
        ):
            continue
        kept[row[id_field]] = row

    invalid: set[str] = set()
    successors: dict[str, list[str]] = {}
    for row_id, row in kept.items():
        parent = row.get(supersedes_field)
        if parent is None:
            continue
        successors.setdefault(parent, []).append(row_id)

    # Regla 4: una rama (dos correcciones del mismo padre) invalida la cadena.
    for parent, children in successors.items():
        if len(children) > 1:
            invalid.add(parent)
            invalid.update(children)

    # Regla 4: referencias cross-tenant o a filas de otro tipo también invalidan.
    for row_id, row in kept.items():
        parent = row.get(supersedes_field)
        if parent is None:
            continue
        parent_row = kept.get(parent)
        if parent_row is None:
            continue
        if parent_row.get(tenant_field) != row.get(tenant_field):
            invalid.add(row_id)
            invalid.add(parent)

    # Regla 4: un ciclo invalida a todos sus miembros.
    for row_id in kept:
        seen: list[str] = []
        cursor: str | None = row_id
        while cursor is not None and cursor in kept:
            if cursor in seen:
                invalid.update(seen)
                break
            seen.append(cursor)
            cursor = kept[cursor].get(supersedes_field)

    # Una corrección que desciende de una cadena inválida hereda su invalidez.
    changed = True
    while changed:
        changed = False
        for row_id, row in kept.items():
            parent = row.get(supersedes_field)
            if row_id not in invalid and parent is not None and parent in invalid:
                invalid.add(row_id)
                changed = True

    superseded = {parent for parent, children in successors.items() if parent in kept and children}
    leaves = [
        row for row_id, row in kept.items() if row_id not in superseded and row_id not in invalid
    ]
    # Regla 5: empates de ingesta se ordenan por UUID solo para reproducir.
    leaves.sort(key=lambda row: (row[ingested_field], row[id_field]))
    return Projection(tuple(leaves), frozenset(invalid))
