"""Smart defaults: what value is usual enough to suggest (SPEC 6.2-6.8).

Pure functions over already-loaded rows. Nothing here reads a database, a clock
or a configuration file; a caller passes the history, the cutoff and the secret,
and gets a decision plus the evidence behind it.

The estimator is deliberately unable to confirm itself: an accepted suggestion
and an edited suggestion are both excluded from the window that produces the
next one (FUNDAMENTOS 7).
"""

from ml.defaults.audit import AuditAssignment, assign_audit_mode
from ml.defaults.estimator import (
    DefaultDecision,
    DefaultStatus,
    PosteriorEstimate,
    compute_binary_default,
    compute_categorical_default,
    compute_default_decision,
    estimate_from_history,
)
from ml.defaults.window import (
    EligibleHistory,
    Stratum,
    eligible_history,
    observation_is_eligible,
)

__all__ = [
    "AuditAssignment",
    "DefaultDecision",
    "DefaultStatus",
    "EligibleHistory",
    "PosteriorEstimate",
    "Stratum",
    "assign_audit_mode",
    "compute_binary_default",
    "compute_categorical_default",
    "compute_default_decision",
    "eligible_history",
    "estimate_from_history",
    "observation_is_eligible",
]
