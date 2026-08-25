"""The data quality index (SPEC 7.1).

`DQI = coverage * recency * consistency`, and the product is deliberate: a
perfect coverage does not compensate for a record that is two weeks old
(FUNDAMENTOS 10.4).

The DQI describes quality. It is never a predictive feature and never a gate:
v0.3 defines no universal cut, so a track abstains for its own explicit reasons,
not because a quality number fell below something.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

from ml.errors import OriginMixError
from ml.spec_constants import (
    DQI_ACCEPTED_DEFAULT_WEIGHT,
    DQI_CONSISTENCY_FLOOR,
    DQI_OBSERVED_WEIGHT,
    DQI_RECENCY_HALF_LIFE_DAYS,
    DQI_UNKNOWN_WEIGHT,
    DQI_WINDOW_DAYS,
)
from packages.shared.canonical import in_window, inclusive_window, local_date
from packages.shared.domain.observation import DataQuality, FieldObservation
from packages.shared.enums import DataOrigin, EntryMode, FieldCode, FieldKind, Source
from packages.shared.field_catalog import DQI_REQUIRED_FIELDS, FIELD_CATALOG
from packages.shared.projection import project_as_of, unique_active

# SPEC 7.1. An accepted suggestion counts half because the person was anchored;
# an edited one counts fully because they overrode it.
ENTRY_MODE_COVERAGE_WEIGHT: MappingProxyType[EntryMode, float] = MappingProxyType(
    {
        EntryMode.MANUAL_NO_DEFAULT: DQI_OBSERVED_WEIGHT,
        EntryMode.AUDIT_MANUAL: DQI_OBSERVED_WEIGHT,
        EntryMode.PROFESSIONAL_OBSERVED: DQI_OBSERVED_WEIGHT,
        EntryMode.IMPORTED_OBSERVED: DQI_OBSERVED_WEIGHT,
        EntryMode.DEFAULT_EDITED: DQI_OBSERVED_WEIGHT,
        EntryMode.DEFAULT_ACCEPTED: DQI_ACCEPTED_DEFAULT_WEIGHT,
        EntryMode.EXPLICIT_UNKNOWN: DQI_UNKNOWN_WEIGHT,
    }
)


@dataclass(frozen=True, slots=True)
class FieldDay:
    """One field on one local date, with at most one value per source."""

    field_code: FieldCode
    local_date: date
    values: dict[Source, object]
    weight: float


def _normalised_disagreement(field_code: FieldCode, left: object, right: object) -> float:
    """Distance in [0,1] for the field's kind (SPEC 7.1).

    A nominal disagreement is all or nothing. Categories are never averaged to
    smooth a conflict away; the index only measures that the conflict exists.
    """

    spec = FIELD_CATALOG[field_code]
    if spec.kind in {FieldKind.NOMINAL, FieldKind.BOOLEAN}:
        return 0.0 if left == right else 1.0
    if spec.kind is FieldKind.ORDINAL:
        span = (spec.maximum or 5) - (spec.minimum or 1)
        return abs(float(left) - float(right)) / float(span)  # type: ignore[arg-type]
    legal_range = spec.legal_range
    if not legal_range:
        return 0.0 if left == right else 1.0
    return min(1.0, abs(float(left) - float(right)) / legal_range)  # type: ignore[arg-type]


def _field_days(
    observations: Iterable[FieldObservation],
    *,
    cutoff: datetime,
    required_fields: Sequence[FieldCode],
) -> tuple[list[FieldDay], bool]:
    """Project, keep the window and the required fields, group by field and day."""

    projection = project_as_of(observations, cutoff)
    window = inclusive_window(local_date(cutoff), DQI_WINDOW_DAYS)
    required = set(required_fields)

    scoped = [
        row
        for row in projection.leaves
        if row.field_code in required
        and in_window(row.local_date, window)
        and FIELD_CATALOG[row.field_code].allows(row.source)
    ]
    grouped = unique_active(
        project_as_of(scoped, cutoff),
        key=lambda row: (row.field_code, row.source, row.local_date),
    )
    clean = grouped.is_clean

    by_field_day: dict[tuple[FieldCode, date], dict[Source, FieldObservation]] = {}
    for row in grouped.rows.values():
        by_field_day.setdefault((row.field_code, row.local_date), {})[row.source] = row

    days: list[FieldDay] = []
    for (field_code, day), by_source in sorted(by_field_day.items(), key=lambda item: str(item[0])):
        weight = max(ENTRY_MODE_COVERAGE_WEIGHT[row.entry_mode] for row in by_source.values())
        values = {source: row.value for source, row in by_source.items() if row.value is not None}
        days.append(FieldDay(field_code=field_code, local_date=day, values=values, weight=weight))
    return days, clean


def compute_dqi(
    observations: Iterable[FieldObservation],
    *,
    as_of_at: datetime,
    required_fields: Sequence[FieldCode] = DQI_REQUIRED_FIELDS,
    window_days: int = DQI_WINDOW_DAYS,
) -> DataQuality:
    """Coverage, recency and consistency over the projected 14-day window.

    The denominator is fixed at `len(required_fields) * window_days`, so a new
    subject with one good day does not score as well covered.
    """

    rows = list(observations)
    origins = {row.data_origin for row in rows}
    if origins == {DataOrigin.REAL, DataOrigin.SYNTHETIC}:
        raise OriginMixError("a quality index never mixes real and synthetic rows")

    days, clean = _field_days(rows, cutoff=as_of_at, required_fields=required_fields)
    cutoff_date = local_date(as_of_at)

    denominator = float(len(required_fields) * window_days)
    coverage = sum(day.weight for day in days) / denominator if denominator else 0.0
    coverage = min(1.0, coverage)

    observed_days = [day.local_date for day in days if day.weight > 0.0 and day.values]
    if observed_days:
        days_since: int | None = (cutoff_date - max(observed_days)).days
        recency = math.exp(-math.log(2.0) * days_since / DQI_RECENCY_HALF_LIFE_DAYS)
    else:
        days_since = None
        recency = 0.0

    disagreements: list[float] = []
    for day in days:
        if len(day.values) < 2:
            continue
        sources = sorted(day.values, key=str)
        pairs = [
            _normalised_disagreement(day.field_code, day.values[left], day.values[right])
            for index, left in enumerate(sources)
            for right in sources[index + 1 :]
        ]
        disagreements.append(sum(pairs) / len(pairs))

    if disagreements:
        mean_disagreement = sum(disagreements) / len(disagreements)
        consistency = max(DQI_CONSISTENCY_FLOOR, 1.0 - mean_disagreement)
    else:
        consistency = 1.0

    return DataQuality(
        coverage=coverage,
        recency=recency,
        consistency=consistency,
        dqi=coverage * recency * consistency,
        window_days=window_days,
        required_fields=tuple(required_fields),
        days_since_last_observation=days_since,
        overlapping_field_days=len(disagreements),
        detail={
            "projection_clean": clean,
            "observed_field_days": len(days),
            "denominator": denominator,
        },
    )
