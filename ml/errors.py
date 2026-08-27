"""Domain exceptions. Only the API layer turns one into an HTTP status.

Most of what could go wrong in v0.3 is not an exception: an abstention is a
normal return value with a reason (SPEC 2.11). These are reserved for inputs
that break the contract itself.
"""

from __future__ import annotations


class FaroError(Exception):
    """Base error for expected Faro domain failures."""

    code = "faro_error"


class ContractViolationError(FaroError):
    """Input violates the published contract."""

    code = "contract_violation"


class InsufficientDataError(FaroError):
    """A computation cannot proceed and has no abstention path to return."""

    code = "insufficient_data"


class ModelNotReadyError(FaroError):
    """Inference was requested before an artifact was loaded."""

    code = "model_not_ready"


class OriginMixError(ContractViolationError):
    """Real and synthetic data met somewhere they must never meet (SPEC 2.2)."""

    code = "synthetic_row_in_real_snapshot"


class CohortViolationError(ContractViolationError):
    """A simulation artifact was pointed at a real subject (SPEC 2.14)."""

    code = "real_subject_not_allowed_in_demo"


class UnmappedSourceValueError(ContractViolationError):
    """An import carried a category the versioned mapping does not know.

    It fails instead of becoming `null`: a value nobody mapped is not the same
    fact as a value nobody reported (SPEC 5.3).
    """

    code = "unmapped_source_value"


class EntryModeNotDerivableError(ContractViolationError):
    """The interaction and session do not determine one entry mode (SPEC 5.5)."""

    code = "entry_mode_not_derivable"
