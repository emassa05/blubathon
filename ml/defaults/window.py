"""The clean window a default is estimated from.

Sixty inclusive calendar days, projected to the cutoff, stratified by tenant,
subject, source and field. Nothing crosses a stratum: two contexts are two
different questions, and two tenants are two different organisations.

What counts is provenance, not volume. A suggestion the person accepted, a
suggestion they edited, a synthetic row, an explicit unknown and an absent day
all contribute nothing, because counting them would let the estimator confirm
its own suggestion (FUNDAMENTOS 7).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ml.spec_constants import DEFAULT_WINDOW_DAYS
from packages.shared.canonical import in_window, inclusive_window, local_date
from packages.shared.domain.observation import DEFAULT_ESTIMATOR_MODES, FieldObservation
from packages.shared.enums import DataOrigin, EntryMode, FieldCode, Source
from packages.shared.projection import ChainConflict, Projection, project_as_of, unique_active


@dataclass(frozen=True, slots=True)
class Stratum:
    """The only grouping a default posterior is computed within."""

    tenant_id: UUID
    subject_id: UUID
    source: Source
    field_code: FieldCode


@dataclass(frozen=True, slots=True)
class EligibleHistory:
    """Rows that may inform a suggestion, plus any conflict that stops them.

    `observations` is empty when the history conflicts: a stratum with two
    active leaves for one day has no defensible count, so it produces no
    suggestion rather than a guessed one.
    """

    stratum: Stratum
    observations: tuple[FieldObservation, ...]
    conflicts: tuple[ChainConflict, ...]
    window_days: int

    @property
    def n_observations(self) -> int:
        return len(self.observations)

    @property
    def is_clean(self) -> bool:
        return not self.conflicts


def observation_is_eligible(
    observation: FieldObservation,
    *,
    approved_mapping_ids: frozenset[UUID],
) -> bool:
    """Which entry modes and origins may inform a suggestion."""

    if observation.data_origin is not DataOrigin.REAL:
        return False
    if observation.entry_mode not in DEFAULT_ESTIMATOR_MODES:
        return False
    if observation.value is None:
        return False
    if observation.entry_mode is EntryMode.IMPORTED_OBSERVED:
        return observation.source_mapping_id in approved_mapping_ids
    return True


def eligible_history(
    observations: Iterable[FieldObservation],
    *,
    stratum: Stratum,
    cutoff: datetime,
    approved_mapping_ids: frozenset[UUID] = frozenset(),
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> EligibleHistory:
    """Project to the cutoff, restrict to the stratum and the window, then filter."""

    projection = project_as_of(observations, cutoff)
    window = inclusive_window(local_date(cutoff), window_days)

    in_stratum = [
        row
        for row in projection.leaves
        if (row.tenant_id, row.subject_id, row.source, row.field_code)
        == (stratum.tenant_id, stratum.subject_id, stratum.source, stratum.field_code)
        and in_window(row.local_date, window)
    ]

    grouped = unique_active(
        Projection(cutoff=cutoff, leaves=tuple(in_stratum), conflicts=()),
        key=lambda row: (row.field_code, row.source, row.local_date),
    )
    if not grouped.is_clean:
        return EligibleHistory(
            stratum=stratum,
            observations=(),
            conflicts=grouped.conflicts,
            window_days=window_days,
        )

    eligible = tuple(
        sorted(
            (
                row
                for row in grouped.rows.values()
                if observation_is_eligible(row, approved_mapping_ids=approved_mapping_ids)
            ),
            key=lambda row: (row.local_date, str(row.field_observation_id)),
        )
    )
    return EligibleHistory(
        stratum=stratum,
        observations=eligible,
        conflicts=projection.conflicts,
        window_days=window_days,
    )
