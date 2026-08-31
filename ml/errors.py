"""Domain exceptions. Only the API layer turns one into an HTTP status.

Most of what could go wrong in v0.3 is not an exception: an abstention is a
normal return value with a reason. These are reserved for inputs
that break the contract itself.
"""

from __future__ import annotations


class BlubathonError(Exception):
    """Base error for expected Blubathon domain failures."""

    code = "blubathon_error"


class ContractViolationError(BlubathonError):
    """Input violates the published contract."""

    code = "contract_violation"


class InsufficientDataError(BlubathonError):
    """A computation cannot proceed and has no abstention path to return."""

    code = "insufficient_data"


class ModelNotReadyError(BlubathonError):
    """Inference was requested before an artifact was loaded."""

    code = "model_not_ready"


class OriginMixError(ContractViolationError):
    """Real and synthetic data met somewhere they must never meet."""

    code = "synthetic_row_in_real_snapshot"


class CohortViolationError(ContractViolationError):
    """A simulation artifact was pointed at a real subject."""

    code = "real_subject_not_allowed_in_demo"


class UnmappedSourceValueError(ContractViolationError):
    """An import carried a category the versioned mapping does not know.

    It fails instead of becoming `null`: a value nobody mapped is not the same
    fact as a value nobody reported.
    """

    code = "unmapped_source_value"


class EntryModeNotDerivableError(ContractViolationError):
    """The interaction and session do not determine one entry mode."""

    code = "entry_mode_not_derivable"
