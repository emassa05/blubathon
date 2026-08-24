"""Domain exceptions translated to HTTP only by the API layer."""


class FaroError(Exception):
    """Base error for expected Faro domain failures."""

    code = "faro_error"


class InsufficientDataError(FaroError):
    """Raised when a computation cannot proceed with the available data."""

    code = "insufficient_data"


class ContractViolationError(FaroError):
    """Raised when input violates the frozen data contract."""

    code = "contract_violation"


class ModelNotReadyError(FaroError):
    """Raised when inference is requested before fitting a model."""

    code = "model_not_ready"
