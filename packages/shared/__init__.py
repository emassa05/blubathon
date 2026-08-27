"""The single executable contract shared by every Blubathon process.

`packages/shared` never imports `ml`, `rag` or `apps`. It owns
the constants, the closed vocabularies, the field catalogue, the canonical bytes
and hashes, the append-only projection, the Spanish copy and the Pydantic models
that every other package reads.

The generated JSON Schema and TypeScript/Zod types under `generated/` come from
these same models; they are never edited by hand
(`python -m tools.contracts.generate`).
"""

from packages.shared import canonical, constants, enums, field_catalog, projection, texts
from packages.shared.constants import (
    CONSTANTS,
    CONTRACT_VERSION,
    DEFAULTS_ESTIMATOR_VERSION,
    DOMAIN_VERSION,
    FORM_POLICY_VERSION,
    SCENARIO_BUILDER_VERSION,
    SCENARIO_SCHEMA_VERSION,
    ConstantSpec,
    constant,
)
from packages.shared.models import *  # noqa: F403
from packages.shared.models import __all__ as _MODEL_EXPORTS

__all__ = [
    "CONSTANTS",
    "CONTRACT_VERSION",
    "DEFAULTS_ESTIMATOR_VERSION",
    "FORM_POLICY_VERSION",
    "SCENARIO_BUILDER_VERSION",
    "SCENARIO_SCHEMA_VERSION",
    "DOMAIN_VERSION",
    "ConstantSpec",
    "canonical",
    "constant",
    "constants",
    "enums",
    "field_catalog",
    "projection",
    "texts",
    *_MODEL_EXPORTS,
]
