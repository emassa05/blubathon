"""Formula-internal constants for the pure ML domain.

The shared normative registry is `packages/shared/constants.py` (SPEC 15,
C01-C50) and is re-exported here so a formula reads one value, not a copy
(CONVENTIONS 7). What lives *here* is the arithmetic that only the domain needs:
derived factors, version labels of the estimators and the closed support tables
a posterior is computed over.

`ml` never imports `apps`, HTTP, SQL or React (CONVENTIONS 4).
"""

from __future__ import annotations

from scipy.stats import norm

from packages.shared.constants import (
    BASELINE_LOWER_QUANTILE,
    BASELINE_MIN_OUTCOMES,
    BASELINE_UPPER_QUANTILE,
    BASELINE_WINDOW_DAYS,
    CATEGORICAL_ANOMALY_PROBABILITY,
    CHALLENGER_L2_GRID,
    CHALLENGER_TIE_TOLERANCE,
    DEFAULT_AUDIT_RATE,
    DEFAULT_LOWER_QUANTILE,
    DEFAULT_LOWER_THRESHOLD,
    DEFAULT_PRIOR_PER_CATEGORY,
    DEFAULT_WINDOW_DAYS,
    DEFAULTS_ESTIMATOR_VERSION,
    DQI_ACCEPTED_DEFAULT_WEIGHT,
    DQI_CONSISTENCY_FLOOR,
    DQI_RECENCY_HALF_LIFE_DAYS,
    DQI_WINDOW_DAYS,
    EVAL_BOOTSTRAP_REPLICATES,
    EVAL_INTERVAL_LEVEL,
    EVAL_MIN_VALID_BOOTSTRAP_FRACTION,
    FORM_HIGHLIGHTED_DEFAULT,
    FORM_HIGHLIGHTED_LOW_COVERAGE,
    GROUP_METRIC_MIN_NEGATIVES,
    GROUP_METRIC_MIN_POSITIVES,
    GROUP_METRIC_MIN_SUBJECTS,
    LOW_COVERAGE_THRESHOLD,
    OFFLINE_RANDOM_SEED,
    PERSONAL_DEVIATION_WINDOW_DAYS,
    PERSONAL_MIN_OBSERVATIONS,
    ROBUST_Z_ANOMALY,
    STALENESS_CEILING_DAYS,
)

__all__ = [
    "AUDIT_BUCKET_MODULUS",
    "AUDIT_BUCKET_THRESHOLD",
    "BASELINE_LOWER_QUANTILE",
    "BASELINE_MIN_OUTCOMES",
    "BASELINE_UPPER_QUANTILE",
    "BASELINE_WINDOW_DAYS",
    "CATEGORICAL_ANOMALY_PROBABILITY",
    "CHALLENGER_L2_GRID",
    "CHALLENGER_TIE_TOLERANCE",
    "DEFAULTS_ESTIMATOR_VERSION",
    "DEFAULT_AUDIT_RATE",
    "DEFAULT_LOWER_QUANTILE",
    "DEFAULT_LOWER_THRESHOLD",
    "DEFAULT_PRIOR_PER_CATEGORY",
    "DEFAULT_WINDOW_DAYS",
    "DQI_ACCEPTED_DEFAULT_WEIGHT",
    "DQI_CONSISTENCY_FLOOR",
    "DQI_OBSERVED_WEIGHT",
    "DQI_RECENCY_HALF_LIFE_DAYS",
    "DQI_UNKNOWN_WEIGHT",
    "DQI_WINDOW_DAYS",
    "EVAL_BOOTSTRAP_REPLICATES",
    "EVAL_INTERVAL_LEVEL",
    "EVAL_MIN_VALID_BOOTSTRAP_FRACTION",
    "EXPLORATION_WEEKDAY_MODULUS",
    "FORM_HIGHLIGHTED_DEFAULT",
    "FORM_HIGHLIGHTED_LOW_COVERAGE",
    "FORM_MAX_MONITORED_HIGHLIGHTS",
    "GROUP_METRIC_MIN_NEGATIVES",
    "GROUP_METRIC_MIN_POSITIVES",
    "GROUP_METRIC_MIN_SUBJECTS",
    "LOW_COVERAGE_THRESHOLD",
    "MAD_TO_SIGMA",
    "OFFLINE_RANDOM_SEED",
    "PERSONAL_DEVIATION_WINDOW_DAYS",
    "PERSONAL_MIN_OBSERVATIONS",
    "ROBUST_Z_ANOMALY",
    "STALENESS_CEILING_DAYS",
]

# SPEC 6.11 [M]: 1 / NormalPPF(0.75) ~= 1.4826 makes the MAD comparable to a
# standard deviation under a normal distribution. Computed, never typed in, so
# it cannot drift from the identity it comes from.
MAD_TO_SIGMA: float = 1.0 / float(norm.ppf(0.75))

# SPEC 6.8: `bucket = HMAC(...) mod 1000`, audited when `bucket < 100`. The
# threshold is the rate expressed in the same units as the bucket.
AUDIT_BUCKET_MODULUS = 1000
AUDIT_BUCKET_THRESHOLD = round(DEFAULT_AUDIT_RATE * AUDIT_BUCKET_MODULUS)

# SPEC 6.10: one weekday per ISO week.
EXPLORATION_WEEKDAY_MODULUS = 7

# SPEC 6.9: normally 2 or 3 highlights, expanded to cover every stale field, but
# never more than 5 monitored fields, because there are only 5 of them.
FORM_MAX_MONITORED_HIGHLIGHTS = 5

# SPEC 7.1 coverage weights. An accepted default counts half because the person
# was anchored; an unknown or absent day contributes nothing at all.
DQI_OBSERVED_WEIGHT = 1.0
DQI_UNKNOWN_WEIGHT = 0.0
