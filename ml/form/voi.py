"""Value of information: which question could change the estimate most.

The default estimator answers "what is the usual value". VoI answers a different
question: "which answer would tell us most about the outcome". A variable can
have a reliable default and still be worth asking, because the point of asking
is to catch the exception.

Unavailable is `None`, never zero. Zero would claim the quantity was computed
and found uninformative; `None` says it could not be computed honestly.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ml.defaults.window import EligibleHistory
from ml.formula_constants import DEFAULT_PRIOR_PER_CATEGORY
from packages.shared.constants import DEFAULTS_ESTIMATOR_VERSION
from packages.shared.domain.prediction import VoiEstimate
from packages.shared.enums import FieldCode, VoiStatus
from packages.shared.field_catalog import FieldValue, closed_support


class ConditionalOutcomeModel(Protocol):
    """A model that can answer `P(Y=1 | X=x, rest of the snapshot unchanged)`.

    This is a conditional query, not an intervention: fixing an answer and
    reading the estimate is not the same as changing the world.
    """

    @property
    def model_version(self) -> str: ...

    def supports(self, field_code: FieldCode) -> bool: ...

    def conditional_probability(self, field_code: FieldCode, value: FieldValue) -> float | None: ...


def binary_entropy(probability: float) -> float:
    """`h(p) = -p ln p - (1-p) ln(1-p)` in nats, with `0 * ln 0 = 0`."""

    if not 0.0 <= probability <= 1.0:
        raise ValueError("a probability outside [0,1] has no entropy")
    if probability in (0.0, 1.0):
        return 0.0
    return -probability * math.log(probability) - (1.0 - probability) * math.log(1.0 - probability)


def compute_predictive_voi(values: Sequence[float], probabilities: Sequence[float]) -> float:
    """`VoI(X) = h(p_bar) - sum_j q_j h(p_j)`, in nats.

    `values` is `q`, the posterior mean over the field's full support;
    `probabilities` is `p`, the conditional outcome probability for each value.
    Numerical error below zero is clipped, because mutual information cannot be
    negative.
    """

    if len(values) != len(probabilities):
        raise ValueError("q and p must have the same length")
    if not values:
        raise ValueError("VoI needs at least one candidate value")
    if any(weight < 0.0 for weight in values):
        raise ValueError("q cannot contain a negative weight")
    if abs(sum(values) - 1.0) > 1e-6:
        raise ValueError("q must sum to one")
    if any(not 0.0 <= probability <= 1.0 for probability in probabilities):
        raise ValueError("p must lie in [0,1]")

    pairs = list(zip(values, probabilities, strict=True))
    p_bar = sum(weight * probability for weight, probability in pairs)
    conditional = sum(weight * binary_entropy(probability) for weight, probability in pairs)
    return max(0.0, binary_entropy(p_bar) - conditional)


@dataclass(frozen=True, slots=True)
class AnswerDistribution:
    """`q_j`, the posterior mean of each value over the field's full support."""

    field_code: FieldCode
    support: tuple[FieldValue, ...]
    weights: tuple[float, ...]
    n_observations: int
    estimator_version: str = DEFAULTS_ESTIMATOR_VERSION

    def as_mapping(self) -> dict[FieldValue, float]:
        return dict(zip(self.support, self.weights, strict=True))


def answer_distribution(
    history: EligibleHistory, *, prior: int = DEFAULT_PRIOR_PER_CATEGORY
) -> AnswerDistribution | None:
    """Dirichlet posterior mean over the closed support of the field.

    Computed from the same clean 60-day window and stratum the defaults use, and
    computed even when the field is not on the default allowlist: VoI orders
    questions, it does not decide whether a suggestion is shown.
    """

    field_code = history.stratum.field_code
    support = closed_support(field_code)
    if support is None or not history.is_clean:
        return None

    counts = Counter(row.value for row in history.observations)
    alphas = [float(prior + counts.get(value, 0)) for value in support]
    total = sum(alphas)
    return AnswerDistribution(
        field_code=field_code,
        support=tuple(support),
        weights=tuple(alpha / total for alpha in alphas),
        n_observations=sum(counts.get(value, 0) for value in support),
    )


def estimate_voi(
    history: EligibleHistory,
    *,
    model: ConditionalOutcomeModel | None,
    cutoff: datetime,
) -> VoiEstimate:
    """VoI for one field, or the explicit reason it is unavailable."""

    field_code = history.stratum.field_code

    if closed_support(field_code) is None:
        return VoiEstimate(field_code=field_code, status=VoiStatus.UNAVAILABLE_FIELD_TYPE)
    if model is None:
        return VoiEstimate(field_code=field_code, status=VoiStatus.UNAVAILABLE_MODEL)
    if not model.supports(field_code):
        return VoiEstimate(field_code=field_code, status=VoiStatus.UNAVAILABLE_MODEL)

    distribution = answer_distribution(history)
    if distribution is None:
        return VoiEstimate(field_code=field_code, status=VoiStatus.UNAVAILABLE_PREDICTION)

    probabilities: list[float] = []
    for value in distribution.support:
        probability = model.conditional_probability(field_code, value)
        if probability is None:
            return VoiEstimate(field_code=field_code, status=VoiStatus.UNAVAILABLE_PREDICTION)
        probabilities.append(probability)

    nats = compute_predictive_voi(list(distribution.weights), probabilities)
    return VoiEstimate(
        field_code=field_code,
        status=VoiStatus.AVAILABLE,
        voi_nats=nats,
        q_estimator_version=distribution.estimator_version,
        conditional_model_version=model.model_version,
        cutoff_at=cutoff,
    )


def voi_by_field(
    histories: Mapping[FieldCode, EligibleHistory],
    *,
    model: ConditionalOutcomeModel | None,
    cutoff: datetime,
) -> dict[FieldCode, VoiEstimate]:
    """VoI for every field the form might ask about."""

    return {
        field_code: estimate_voi(history, model=model, cutoff=cutoff)
        for field_code, history in histories.items()
    }


__all__ = [
    "AnswerDistribution",
    "ConditionalOutcomeModel",
    "answer_distribution",
    "binary_entropy",
    "compute_predictive_voi",
    "estimate_voi",
    "voi_by_field",
]
