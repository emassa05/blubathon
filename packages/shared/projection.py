"""`project_as_of`: the one append-only view every formula reads.

A correction never overwrites history; it appends a row that points at the one it
supersedes. Reading at a cutoff therefore means: keep what was known then, follow
each correction chain to its single active leaf, and refuse to guess when the
history is not a chain.

Refusing matters more than resolving. A branch, a cycle, a cross-tenant pointer
or a chain that changes entity kind is a conflict, and a conflict is reported,
never silently aggregated.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

ConflictReason = Literal[
    "branch",
    "cycle",
    "cross_tenant",
    "incompatible_kind",
    "duplicate_active_leaf",
]


@runtime_checkable
class AppendOnlyRow(Protocol):
    """What a projectable row must expose.

    `effective_instant` is the row's own semantic time when it has one: an
    observation applies at `effective_at`, a report at `reported_at`. Rows whose
    only time is ingestion return `None`.
    """

    tenant_id: UUID
    ingested_at: datetime
    supersedes_id: UUID | None

    @property
    def record_id(self) -> UUID: ...

    @property
    def record_kind(self) -> str: ...

    @property
    def effective_instant(self) -> datetime | None: ...


@dataclass(frozen=True, slots=True)
class ChainConflict:
    """A correction history that cannot be resolved into one active leaf."""

    reason: ConflictReason
    record_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class Projection[RowT]:
    """The active leaves at a cutoff plus every chain that refused to resolve."""

    cutoff: datetime
    leaves: tuple[RowT, ...]
    conflicts: tuple[ChainConflict, ...]

    @property
    def is_clean(self) -> bool:
        return not self.conflicts

    @property
    def projected_ids(self) -> tuple[UUID, ...]:
        """Exact IDs a snapshot persists so it is never recomputed."""

        return tuple(row.record_id for row in self.leaves)


def _visible(row: AppendOnlyRow, cutoff: datetime) -> bool:
    if row.ingested_at > cutoff:
        return False
    effective = row.effective_instant
    return not (effective is not None and effective > cutoff)


def _sort_key(row: AppendOnlyRow) -> tuple[datetime, str]:
    # Ingest ties order by UUID only so a diagnostic is reproducible; the order
    # never decides which of two active leaves wins, because neither does.
    return (row.ingested_at, str(row.record_id))


def project_as_of[RowT: AppendOnlyRow](rows: Iterable[RowT], cutoff: datetime) -> Projection[RowT]:
    """Resolve append-only history to the leaves known at `cutoff`."""

    visible = sorted((row for row in rows if _visible(row, cutoff)), key=_sort_key)
    by_id: dict[UUID, RowT] = {row.record_id: row for row in visible}

    conflicts: list[ChainConflict] = []
    superseded_by: dict[UUID, list[RowT]] = {}
    for row in visible:
        if row.supersedes_id is not None:
            superseded_by.setdefault(row.supersedes_id, []).append(row)

    invalid: set[UUID] = set()

    for target, children in superseded_by.items():
        if len(children) > 1:
            members = tuple(sorted((child.record_id for child in children), key=str))
            conflicts.append(ChainConflict(reason="branch", record_ids=(target, *members)))
            invalid.add(target)
            invalid.update(members)

    for row in visible:
        parent_id = row.supersedes_id
        if parent_id is None:
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            # The superseded row is not known at this cutoff, so this row is the
            # root of its own visible chain. Nothing to reconcile.
            continue
        if parent.tenant_id != row.tenant_id:
            conflicts.append(
                ChainConflict(reason="cross_tenant", record_ids=(parent.record_id, row.record_id))
            )
            invalid.update({parent.record_id, row.record_id})
        if parent.record_kind != row.record_kind:
            conflicts.append(
                ChainConflict(
                    reason="incompatible_kind", record_ids=(parent.record_id, row.record_id)
                )
            )
            invalid.update({parent.record_id, row.record_id})

    for row in visible:
        cycle = _detect_cycle(row, by_id)
        if cycle is not None:
            conflicts.append(ChainConflict(reason="cycle", record_ids=cycle))
            invalid.update(cycle)

    superseded_ids = {
        target for target, children in superseded_by.items() if target in by_id and children
    }
    leaves = tuple(
        row
        for row in visible
        if row.record_id not in superseded_ids and row.record_id not in invalid
    )
    return Projection(cutoff=cutoff, leaves=leaves, conflicts=_dedupe(conflicts))


def _detect_cycle[RowT: AppendOnlyRow](
    start: RowT, by_id: dict[UUID, RowT]
) -> tuple[UUID, ...] | None:
    seen: list[UUID] = []
    current: RowT | None = start
    while current is not None:
        if current.record_id in seen:
            index = seen.index(current.record_id)
            return tuple(sorted(seen[index:], key=str))
        seen.append(current.record_id)
        parent_id = current.supersedes_id
        current = by_id.get(parent_id) if parent_id is not None else None
    return None


def _dedupe(conflicts: Sequence[ChainConflict]) -> tuple[ChainConflict, ...]:
    unique: dict[tuple[ConflictReason, tuple[UUID, ...]], ChainConflict] = {}
    for conflict in conflicts:
        unique.setdefault((conflict.reason, conflict.record_ids), conflict)
    return tuple(
        sorted(unique.values(), key=lambda item: (item.reason, tuple(map(str, item.record_ids))))
    )


@dataclass(frozen=True, slots=True)
class UniqueActive[KeyT, RowT]:
    """At most one active row per key, plus the keys that had more than one."""

    rows: dict[KeyT, RowT]
    conflicts: tuple[ChainConflict, ...]

    @property
    def is_clean(self) -> bool:
        return not self.conflicts


def unique_active[RowT: AppendOnlyRow, KeyT: Hashable](
    projection: Projection[RowT], key: Callable[[RowT], KeyT]
) -> UniqueActive[KeyT, RowT]:
    """Group leaves by key, reporting duplicates instead of picking a winner.

    For one field, source and `local_date` at most one observation may
    stay active. Two of them is a conflict a model must not average away.
    """

    grouped: dict[KeyT, list[RowT]] = {}
    for row in projection.leaves:
        grouped.setdefault(key(row), []).append(row)

    rows: dict[KeyT, RowT] = {}
    conflicts: list[ChainConflict] = list(projection.conflicts)
    for group_key, members in grouped.items():
        if len(members) == 1:
            rows[group_key] = members[0]
            continue
        conflicts.append(
            ChainConflict(
                reason="duplicate_active_leaf",
                record_ids=tuple(sorted((member.record_id for member in members), key=str)),
            )
        )
    return UniqueActive(rows=rows, conflicts=_dedupe(conflicts))
