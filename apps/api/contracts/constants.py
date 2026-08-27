"""Re-export del registro de constantes normativas (C01-C50).

El registro vive en `packages/shared/constants.py`, que H1 publicó. Este módulo
no declara ningún valor: reexporta el de P1 para que `apps/**` siga teniendo un
único punto de importación. Un literal del registro no se repite en `apps/`
.
"""

from __future__ import annotations

from packages.shared.constants import (
    API_PREFIX,
    BASELINE_MIN_OUTCOMES,
    CONSTANTS,
    CONSTANTS_BY_NAME,
    CONTRACT_VERSION,
    DECISION_POLICY_VERSION,
    DEFAULT_AUDIT_RATE,
    DEFAULT_LOWER_THRESHOLD,
    DEFAULT_WINDOW_DAYS,
    DEFAULTS_ESTIMATOR_VERSION,
    FORM_HIGHLIGHTED_DEFAULT,
    FORM_HIGHLIGHTED_LOW_COVERAGE,
    FORM_POLICY_VERSION,
    HASH_ALGORITHM,
    LOW_COVERAGE_THRESHOLD,
    MAX_RUNTIME_STRATEGIES,
    OUTCOME_CAPTURE_LIMIT_HOURS,
    PILOT_DATABASE,
    REFERENCE_TIMEZONE,
    SCENARIO_BUILDER_VERSION,
    SCENARIO_SCHEMA_VERSION,
    SPEC_VERSION,
    STALENESS_CEILING_DAYS,
    TARGET_HORIZON_HOURS,
    ConstantSpec,
    DecisionClass,
    constant,
)

__all__ = [
    "API_PREFIX",
    "BASELINE_MIN_OUTCOMES",
    "CONSTANTS",
    "CONSTANTS_BY_NAME",
    "CONTRACT_VERSION",
    "DECISION_POLICY_VERSION",
    "DEFAULTS_ESTIMATOR_VERSION",
    "DEFAULT_AUDIT_RATE",
    "DEFAULT_LOWER_THRESHOLD",
    "DEFAULT_WINDOW_DAYS",
    "FORM_HIGHLIGHTED_DEFAULT",
    "FORM_HIGHLIGHTED_LOW_COVERAGE",
    "FORM_POLICY_VERSION",
    "HASH_ALGORITHM",
    "LOW_COVERAGE_THRESHOLD",
    "MAX_RUNTIME_STRATEGIES",
    "OUTCOME_CAPTURE_LIMIT_HOURS",
    "PILOT_DATABASE",
    "REFERENCE_TIMEZONE",
    "SCENARIO_BUILDER_VERSION",
    "SCENARIO_SCHEMA_VERSION",
    "SPEC_VERSION",
    "STALENESS_CEILING_DAYS",
    "TARGET_HORIZON_HOURS",
    "ConstantSpec",
    "DecisionClass",
    "constant",
]
