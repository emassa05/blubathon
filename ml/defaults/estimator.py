"""Beta and Dirichlet posteriors behind a suggestion.

A binary field is `Beta(1+k, 1+N-k)`; a categorical or ordinal field is
`Dirichlet(1+n_j)` and the candidate's marginal is again a Beta. The two are the
same arithmetic: the binary case is the K=2 marginal.

Blubathon shows the lower bound, not the mean. Two histories with the same mean can
carry very different evidence, and the product rule asks how high the value
still is under a conservative reading of the posterior.

An ordinal keeps its anchors. The estimator never averages categories and never
assumes the distance between 1 and 2 equals the distance between 4 and 5.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from scipy.stats import beta as beta_dist

from ml.defaults.window import EligibleHistory
from ml.formula_constants import (
    DEFAULT_LOWER_QUANTILE,
    DEFAULT_LOWER_THRESHOLD,
    DEFAULT_PRIOR_PER_CATEGORY,
)
from packages.shared.constants import DEFAULTS_ESTIMATOR_VERSION
from packages.shared.domain.observation import PosteriorDefault
from packages.shared.enums import FieldCode, FieldKind
from packages.shared.field_catalog import (
    DEFAULT_ALLOWLIST_V1,
    FIELD_CATALOG,
    KINDS_WITHOUT_DEFAULTS,
    FieldValue,
    closed_support,
)


class DefaultStatus(StrEnum):
    """Why a field did or did not get a suggestion. Diagnostic, not a contract."""

    PRESENTED = "presented"
    SUPPRESSED_AUDIT_MODE = "suppressed_audit_mode"
    SUPPRESSED_NOT_ALLOWLISTED = "suppressed_not_allowlisted"
    SUPPRESSED_FIELD_KIND = "suppressed_field_kind"
    SUPPRESSED_CONFLICT = "suppressed_conflict"
    SUPPRESSED_NO_ELIGIBLE_HISTORY = "suppressed_no_eligible_history"
    SUPPRESSED_TIE = "suppressed_tie"
    SUPPRESSED_BELOW_THRESHOLD = "suppressed_below_threshold"


@dataclass(frozen=True, slots=True)
class PosteriorEstimate:
    """One candidate's marginal posterior, or the fact that there is no candidate."""

    candidate: FieldValue | None
    candidate_count: int
    n_observations: int
    alpha: float
    posterior_beta: float
    posterior_mean: float
    lower_bound: float
    tie: bool

    @property
    def has_candidate(self) -> bool:
        return self.candidate is not None and not self.tie


@dataclass(frozen=True, slots=True)
class DefaultDecision:
    """The product decision and the evidence behind it."""

    field_code: FieldCode
    status: DefaultStatus
    estimate: PosteriorEstimate | None = None
    estimator_version: str = DEFAULTS_ESTIMATOR_VERSION

    @property
    def is_presented(self) -> bool:
        return self.status is DefaultStatus.PRESENTED

    def to_contract(self) -> PosteriorDefault | None:
        """The published `PosteriorDefault`, or `None` when nothing is shown."""

        if not self.is_presented or self.estimate is None or self.estimate.candidate is None:
            return None
        return PosteriorDefault(
            field_code=self.field_code,
            candidate_value=self.estimate.candidate,
            candidate_count=self.estimate.candidate_count,
            n_observations=self.estimate.n_observations,
            posterior_mean=self.estimate.posterior_mean,
            lower_bound=self.estimate.lower_bound,
            quantile=DEFAULT_LOWER_QUANTILE,
            estimator_version=self.estimator_version,
        )


def _marginal(alpha: float, posterior_beta: float, quantile: float) -> tuple[float, float]:
    """Posterior mean and lower quantile of a Beta, from SciPy."""

    mean = alpha / (alpha + posterior_beta)
    lower = float(beta_dist.ppf(quantile, alpha, posterior_beta))
    return mean, lower


def compute_binary_default(
    *,
    true_count: int,
    false_count: int,
    quantile: float = DEFAULT_LOWER_QUANTILE,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> PosteriorEstimate:
    """`p | D ~ Beta(1+k, 1+N-k)` for the more frequent value.

    An exact tie produces no candidate: with `k_true == k_false` there is no
    "usual" answer to suggest.
    """

    if true_count < 0 or false_count < 0:
        raise ValueError("counts cannot be negative")
    n_observations = true_count + false_count
    tie = true_count == false_count
    candidate: FieldValue | None = None
    candidate_count = max(true_count, false_count)
    if not tie:
        candidate = true_count > false_count

    alpha = float(prior + candidate_count)
    posterior_beta = float(prior + n_observations - candidate_count)
    mean, lower = _marginal(alpha, posterior_beta, quantile)
    return PosteriorEstimate(
        candidate=candidate,
        candidate_count=candidate_count,
        n_observations=n_observations,
        alpha=alpha,
        posterior_beta=posterior_beta,
        posterior_mean=mean,
        lower_bound=lower,
        tie=tie,
    )


def compute_categorical_default(
    *,
    counts: Mapping[FieldValue, int],
    support: Sequence[FieldValue],
    quantile: float = DEFAULT_LOWER_QUANTILE,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> PosteriorEstimate:
    """Dirichlet over the closed support, then the candidate's Beta marginal.

    Every category of the support gets its prior even when it was never
    observed, so `A = K*prior + N` and an unobserved category still holds mass.
    """

    if not support:
        raise ValueError("a categorical posterior needs a closed support")
    unknown = set(counts) - set(support)
    if unknown:
        raise ValueError(f"counts contain values outside the support: {sorted(map(str, unknown))}")
    if any(count < 0 for count in counts.values()):
        raise ValueError("counts cannot be negative")

    alphas = {value: float(prior + counts.get(value, 0)) for value in support}
    total = sum(alphas.values())
    n_observations = sum(counts.get(value, 0) for value in support)

    top = max(alphas.values())
    winners = [value for value in support if alphas[value] == top]
    tie = len(winners) > 1
    candidate = None if tie else winners[0]

    alpha = top
    posterior_beta = total - top
    mean, lower = _marginal(alpha, posterior_beta, quantile)
    return PosteriorEstimate(
        candidate=candidate,
        candidate_count=int(top - prior),
        n_observations=n_observations,
        alpha=alpha,
        posterior_beta=posterior_beta,
        posterior_mean=mean,
        lower_bound=lower,
        tie=tie,
    )


def estimate_from_history(
    history: EligibleHistory,
    *,
    quantile: float = DEFAULT_LOWER_QUANTILE,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> PosteriorEstimate:
    """Count the eligible values and run the posterior for the field's kind."""

    field_code = history.stratum.field_code
    support = closed_support(field_code)
    if support is None:
        raise ValueError(f"{field_code} has no closed support and gets no default")

    counts = Counter(row.value for row in history.observations)
    if FIELD_CATALOG[field_code].kind is FieldKind.BOOLEAN:
        return compute_binary_default(
            true_count=counts.get(True, 0),
            false_count=counts.get(False, 0),
            quantile=quantile,
            prior=prior,
        )
    return compute_categorical_default(
        counts=dict(counts), support=support, quantile=quantile, prior=prior
    )


def compute_default_decision(
    history: EligibleHistory,
    *,
    audit_mode: bool,
    threshold: float = DEFAULT_LOWER_THRESHOLD,
    quantile: float = DEFAULT_LOWER_QUANTILE,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> DefaultDecision:
    """The presentation rule, applied in the order it is declared.

    A suggestion appears only when `lower > 0.70` strictly, the field is on the
    allowlist, the session is not audited, and the posterior has no tie.
    """

    field_code = history.stratum.field_code
    spec = FIELD_CATALOG[field_code]

    if audit_mode:
        return DefaultDecision(field_code=field_code, status=DefaultStatus.SUPPRESSED_AUDIT_MODE)
    if field_code not in DEFAULT_ALLOWLIST_V1:
        return DefaultDecision(
            field_code=field_code, status=DefaultStatus.SUPPRESSED_NOT_ALLOWLISTED
        )
    if spec.kind in KINDS_WITHOUT_DEFAULTS or closed_support(field_code) is None:
        return DefaultDecision(field_code=field_code, status=DefaultStatus.SUPPRESSED_FIELD_KIND)
    if not history.is_clean:
        return DefaultDecision(field_code=field_code, status=DefaultStatus.SUPPRESSED_CONFLICT)
    if history.n_observations == 0:
        return DefaultDecision(
            field_code=field_code, status=DefaultStatus.SUPPRESSED_NO_ELIGIBLE_HISTORY
        )

    estimate = estimate_from_history(history, quantile=quantile, prior=prior)
    if not estimate.has_candidate:
        return DefaultDecision(
            field_code=field_code, status=DefaultStatus.SUPPRESSED_TIE, estimate=estimate
        )
    if not estimate.lower_bound > threshold:
        return DefaultDecision(
            field_code=field_code,
            status=DefaultStatus.SUPPRESSED_BELOW_THRESHOLD,
            estimate=estimate,
        )
    return DefaultDecision(field_code=field_code, status=DefaultStatus.PRESENTED, estimate=estimate)
