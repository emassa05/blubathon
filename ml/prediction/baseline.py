"""The personal real baseline.

What this estimates is narrow and the contract says so: the observed rate of the
target among this subject's own previous primary episodes, under the same care
mode and the same target definition version. It is not daily incidence, not
population risk, and not the effect of today's answers.

With the data the repository has today it abstains, and that is the correct
answer rather than a placeholder.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from scipy.stats import beta as beta_dist

from ml.spec_constants import (
    BASELINE_LOWER_QUANTILE,
    BASELINE_MIN_OUTCOMES,
    BASELINE_UPPER_QUANTILE,
    BASELINE_WINDOW_DAYS,
    DEFAULT_PRIOR_PER_CATEGORY,
)
from packages.shared.canonical import in_window, inclusive_window, local_date
from packages.shared.domain.base import Interval
from packages.shared.domain.outcome import OutcomeResolution, qualifies_for_primary_dataset
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.enums import (
    DataOrigin,
    EpisodeRole,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionStatus,
)

BASELINE_MODEL_VERSION = "real-personal-baseline-0.3.0"


@dataclass(frozen=True, slots=True)
class BaselineCandidate:
    """One previous episode and the resolution that was known at the cutoff."""

    episode: PredictionEpisode
    resolution: OutcomeResolution
    consent_authorized: bool


@dataclass(frozen=True, slots=True)
class BaselineEstimate:
    """A probability with its interval, or an abstention with its reasons."""

    status: PredictionStatus
    verified_outcomes: int
    positive_outcomes: int
    probability: float | None = None
    interval: Interval | None = None
    abstention_reasons: tuple[PredictionAbstentionReason, ...] = ()
    model_version: str = BASELINE_MODEL_VERSION

    @property
    def is_visible(self) -> bool:
        return self.status is PredictionStatus.OK


def _in_scope(
    candidate: BaselineCandidate,
    *,
    subject_id: UUID,
    care_mode: str,
    target_definition_version: str,
    window: tuple,
) -> bool:
    episode = candidate.episode
    return (
        episode.subject_id == subject_id
        and episode.role is EpisodeRole.PRIMARY
        and episode.care_mode == care_mode
        and episode.target_definition_version == target_definition_version
        and in_window(local_date(episode.target_start_at), window)
    )


def eligible_outcomes(
    candidates: Iterable[BaselineCandidate],
    *,
    as_of_at: datetime,
    subject_id: UUID,
    care_mode: str,
    target_definition_version: str,
    window_days: int = BASELINE_WINDOW_DAYS,
) -> tuple[list[BaselineCandidate], bool]:
    """Apply every filter, and report whether a conflict is in scope.

    A conflict inside the same window, subject, care mode and target version
    blocks the estimate; conflicts outside that scope do not.
    """

    window = inclusive_window(local_date(as_of_at), window_days)
    in_scope = [
        candidate
        for candidate in candidates
        if _in_scope(
            candidate,
            subject_id=subject_id,
            care_mode=care_mode,
            target_definition_version=target_definition_version,
            window=window,
        )
    ]

    unresolved_conflict = any(
        candidate.resolution.status is OutcomeResolutionStatus.CONFLICTED for candidate in in_scope
    )

    eligible = [
        candidate
        for candidate in in_scope
        if qualifies_for_primary_dataset(candidate.resolution)
        and candidate.episode.input_data_origin is DataOrigin.REAL
        and candidate.consent_authorized
        and candidate.resolution.resolved_at is not None
        and candidate.resolution.resolved_at <= as_of_at
        and candidate.resolution.ingested_at <= as_of_at
    ]
    return eligible, unresolved_conflict


def build_personal_baseline(
    candidates: Iterable[BaselineCandidate],
    *,
    as_of_at: datetime,
    subject_id: UUID,
    care_mode: str | None,
    target_definition_version: str,
    window_days: int = BASELINE_WINDOW_DAYS,
    minimum_outcomes: int = BASELINE_MIN_OUTCOMES,
    prior: int = DEFAULT_PRIOR_PER_CATEGORY,
) -> BaselineEstimate:
    """`p | D ~ Beta(1+e, 1+n-e)` over the subject's own verified outcomes.

    Abstains when there are fewer than five verified outcomes, when a conflict is
    unresolved in scope, or when the care mode history is missing. There is no
    additional interval-width gate: with this prior and minimum the old 0.60 cut
    was unreachable and was retired (C20).
    """

    reasons: list[PredictionAbstentionReason] = []

    if care_mode is None:
        return BaselineEstimate(
            status=PredictionStatus.ABSTAINED,
            verified_outcomes=0,
            positive_outcomes=0,
            abstention_reasons=(PredictionAbstentionReason.CARE_MODE_HISTORY_UNAVAILABLE,),
        )

    eligible, unresolved_conflict = eligible_outcomes(
        candidates,
        as_of_at=as_of_at,
        subject_id=subject_id,
        care_mode=care_mode,
        target_definition_version=target_definition_version,
        window_days=window_days,
    )

    if any(candidate.episode.care_mode is None for candidate in eligible):
        reasons.append(PredictionAbstentionReason.CARE_MODE_HISTORY_UNAVAILABLE)

    verified = len(eligible)
    positives = sum(
        1 for candidate in eligible if candidate.resolution.status is OutcomeResolutionStatus.YES
    )

    if unresolved_conflict:
        reasons.append(PredictionAbstentionReason.UNRESOLVED_CONFLICT)
    if verified < minimum_outcomes:
        reasons.append(PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES)
        reasons.append(PredictionAbstentionReason.COLLECTING_DATA)

    if reasons:
        return BaselineEstimate(
            status=PredictionStatus.ABSTAINED,
            verified_outcomes=verified,
            positive_outcomes=positives,
            abstention_reasons=tuple(dict.fromkeys(reasons)),
        )

    alpha = float(prior + positives)
    posterior_beta = float(prior + verified - positives)
    return BaselineEstimate(
        status=PredictionStatus.OK,
        verified_outcomes=verified,
        positive_outcomes=positives,
        probability=alpha / (alpha + posterior_beta),
        interval=Interval(
            lower=float(beta_dist.ppf(BASELINE_LOWER_QUANTILE, alpha, posterior_beta)),
            upper=float(beta_dist.ppf(BASELINE_UPPER_QUANTILE, alpha, posterior_beta)),
        ),
    )


def personal_rate(values: Sequence[float]) -> float | None:
    """Mean of an observed personal history, or `None` when there is none."""

    if not values:
        return None
    return sum(values) / len(values)
