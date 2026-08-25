"""Subject-clustered bootstrap intervals (SPEC 14.4, C45-C47).

Days of the same child are correlated, so resampling rows would treat one child
seen twenty times as twenty independent children and produce an interval far too
narrow. Each replicate resamples *subjects* with replacement and takes all of
their rows.

Replicates where the statistic is undefined -- a resample that happens to hold
one class, for instance -- are skipped rather than filled in. If fewer than 80%
of replicates are valid, no interval is published at all.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

import numpy as np

from ml.spec_constants import (
    EVAL_BOOTSTRAP_REPLICATES,
    EVAL_INTERVAL_LEVEL,
    EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
    OFFLINE_RANDOM_SEED,
)

T = TypeVar("T")

Statistic = Callable[[Sequence[int], Sequence[float]], float | None]


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    """A percentile interval, or the reason there is none."""

    estimable: bool
    lower: float | None = None
    upper: float | None = None
    valid_replicates: int = 0
    replicates: int = 0
    not_estimable_reason: str | None = None

    @property
    def valid_fraction(self) -> float:
        return self.valid_replicates / self.replicates if self.replicates else 0.0


def cluster_bootstrap(
    statistic: Statistic,
    *,
    labels: Sequence[int],
    probabilities: Sequence[float],
    subject_ids: Sequence[UUID],
    replicates: int = EVAL_BOOTSTRAP_REPLICATES,
    seed: int = OFFLINE_RANDOM_SEED,
    level: float = EVAL_INTERVAL_LEVEL,
    min_valid_fraction: float = EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
) -> BootstrapInterval:
    """Percentile interval over subject resamples, at the declared level."""

    if not (len(labels) == len(probabilities) == len(subject_ids)):
        raise ValueError("labels, probabilities and subject ids must align")
    if not labels:
        return BootstrapInterval(
            estimable=False, replicates=replicates, not_estimable_reason="no_rows"
        )

    by_subject: dict[UUID, list[int]] = {}
    for index, subject_id in enumerate(subject_ids):
        by_subject.setdefault(subject_id, []).append(index)
    subjects = sorted(by_subject, key=str)
    if len(subjects) < 2:
        return BootstrapInterval(
            estimable=False, replicates=replicates, not_estimable_reason="single_subject"
        )

    generator = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(replicates):
        drawn = generator.integers(0, len(subjects), size=len(subjects))
        rows: list[int] = []
        for position in drawn:
            rows.extend(by_subject[subjects[int(position)]])
        value = statistic(
            [labels[index] for index in rows], [probabilities[index] for index in rows]
        )
        if value is not None and np.isfinite(value):
            values.append(float(value))

    if len(values) < min_valid_fraction * replicates:
        return BootstrapInterval(
            estimable=False,
            valid_replicates=len(values),
            replicates=replicates,
            not_estimable_reason="insufficient_valid_bootstrap_replicates",
        )

    tail = (1.0 - level) / 2.0
    lower, upper = np.percentile(values, [100.0 * tail, 100.0 * (1.0 - tail)])
    return BootstrapInterval(
        estimable=True,
        lower=float(lower),
        upper=float(upper),
        valid_replicates=len(values),
        replicates=replicates,
    )
