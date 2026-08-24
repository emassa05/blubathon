"""Las 4 excepciones de FARO. Nada más (CONVENTIONS §6)."""


class FaroError(Exception):
    """Base de todos los errores del dominio ml/."""


class InsufficientDataError(FaroError):
    """SPEC §6 — no hay base suficiente para estimar riesgo."""


class ContractViolationError(FaroError):
    """Datos que rompen el contrato del SPEC §2 (p. ej. assumed_stable con valor)."""


class ModelNotReadyError(FaroError):
    """El modelo no está entrenado / disponible."""
