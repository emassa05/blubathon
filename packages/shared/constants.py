"""The shared normative constants of C01 to C50.

Forbids duplicating a literal from this registry, so every module
level name below reads its value back out of :data:`CONSTANTS` instead of
restating it. A constant carries its decision class because a product policy and
a mathematical identity are not the same kind of claim, and the difference has to
survive into the code that uses them.

`packages/shared` never imports `ml`, `rag` or `apps`. Formula
internals that are not shared decisions live in `ml/spec_constants.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

DecisionClass = Literal["mathematical", "evidence", "policy", "engineering"]

CONTRACT_VERSION = "blubathon-contract-0.4.0"
"""Version of the executable contract published by `packages/shared`.

Distinct from ``SPEC_VERSION``: the specification can be clarified without
regenerating schemas, and a schema change without a specification change is
still a contract change.
"""

FORM_POLICY_VERSION = "form-0.3.0"
"""Version stamped on a form session; it seeds the audit and exploration HMACs."""

DEFAULTS_ESTIMATOR_VERSION = "defaults-0.3.0"
"""Version of the default estimator that produced a `DefaultPresentation`."""

SCENARIO_SCHEMA_VERSION = "scenario-1"
"""The single `ScenarioV1` representation; there is no other."""

SCENARIO_BUILDER_VERSION = "scenario-builder-0.3.0"
"""Version of the pure P1 `build_scenario` facade."""


@dataclass(frozen=True, slots=True)
class ConstantSpec:
    """One normative constant with the class of decision that produced it."""

    constant_id: str
    name: str
    value: Any
    decision_class: DecisionClass
    spec_ref: str
    note: str | None = None


def _spec(
    constant_id: str,
    name: str,
    value: Any,
    decision_class: DecisionClass,
    spec_ref: str,
    note: str | None = None,
) -> ConstantSpec:
    return ConstantSpec(
        constant_id=constant_id,
        name=name,
        value=value,
        decision_class=decision_class,
        spec_ref=spec_ref,
        note=note,
    )


_REGISTRY: tuple[ConstantSpec, ...] = (
    _spec("C01", "SPEC_VERSION", "0.4.0", "engineering", "SPEC 15 / C01"),
    _spec("C02", "API_PREFIX", "/v1", "engineering", "SPEC 11 / C02"),
    _spec("C03", "REFERENCE_TIMEZONE", "America/Santiago", "engineering", "SPEC 5.1 / C03"),
    _spec("C04", "TARGET_HORIZON_HOURS", 24, "policy", "SPEC 4.1 / C04"),
    _spec("C05", "OUTCOME_CAPTURE_LIMIT_HOURS", 48, "policy", "SPEC 4.1 / C05"),
    _spec("C06", "DEFAULT_WINDOW_DAYS", 60, "policy", "SPEC 6.2 / C06"),
    _spec("C07", "DEFAULT_PRIOR_PER_CATEGORY", 1, "policy", "SPEC 6.3 / C07"),
    _spec("C08", "DEFAULT_LOWER_QUANTILE", 0.05, "policy", "SPEC 6.3 / C08"),
    _spec(
        "C09",
        "DEFAULT_LOWER_THRESHOLD",
        0.70,
        "policy",
        "SPEC 6.6 / C09",
        note="strict: a lower bound of exactly 0.70 does not present a suggestion",
    ),
    _spec("C10", "DEFAULT_AUDIT_RATE", 0.10, "policy", "SPEC 6.8 / C10"),
    _spec("C11", "FORM_HIGHLIGHTED_DEFAULT", 2, "policy", "SPEC 6.9 / C11"),
    _spec("C12", "FORM_HIGHLIGHTED_LOW_COVERAGE", 3, "policy", "SPEC 6.9 / C12"),
    _spec("C13", "LOW_COVERAGE_THRESHOLD", 0.50, "policy", "SPEC 6.9 / C13"),
    _spec("C14", "STALENESS_CEILING_DAYS", 7, "policy", "SPEC 6.10 / C14"),
    _spec(
        "C15",
        "EXPLORATION_PERIOD",
        "one_hmac_weekday_per_iso_week",
        "policy",
        "SPEC 6.10 / C15",
        note="frequency is approximately 1/7; a missed weekday is never compensated",
    ),
    _spec("C16", "CATEGORICAL_ANOMALY_PROBABILITY", 0.05, "policy", "SPEC 6.11 / C16"),
    _spec("C17", "ROBUST_Z_ANOMALY", 2.0, "policy", "SPEC 6.11 / C17"),
    _spec("C18", "BASELINE_WINDOW_DAYS", 60, "policy", "SPEC 8.3 / C18"),
    _spec("C19", "BASELINE_MIN_OUTCOMES", 5, "policy", "SPEC 8.5 / C19"),
    _spec(
        "C20",
        "BASELINE_MAX_INTERVAL_WIDTH",
        None,
        "policy",
        "SPEC 8.5 / C20",
        note="gate retired: with this prior and minimum the old 0.60 cut was unreachable",
    ),
    _spec("C21", "PERSONAL_DEVIATION_WINDOW_DAYS", 30, "policy", "SPEC 6.11 / C21"),
    _spec("C22", "PERSONAL_MIN_OBSERVATIONS", 5, "policy", "SPEC 6.11 / C22"),
    _spec(
        "C23",
        "CHALLENGER_MAX_PREDICTORS",
        2,
        "policy",
        "SPEC 8.4 / C23",
        note="preregistered: sleep deviation and regulation deviation",
    ),
    _spec(
        "C24", "CHALLENGER_L2_GRID", (0.01, 0.1, 1.0, 10.0, 100.0), "engineering", "SPEC 8.4 / C24"
    ),
    _spec("C25", "RAG_LEXICAL_TOP_K", 20, "engineering", "SPEC 9.4 / C25"),
    _spec("C26", "RAG_DENSE_TOP_K", 20, "engineering", "SPEC 9.4 / C26"),
    _spec("C27", "RAG_RRF_K", 60, "engineering", "SPEC 9.4 / C27"),
    _spec("C28", "RAG_FINAL_CHUNKS", 8, "engineering", "SPEC 9.4 / C28"),
    _spec("C29", "RUNTIME_LLM_CALLS", 0, "policy", "SPEC 9.1 / C29"),
    _spec("C30", "MAX_RUNTIME_STRATEGIES", 3, "policy", "SPEC 9.8 / C30"),
    _spec(
        "C31",
        "STRATEGY_REQUIRED_DISTINCT_REVIEWERS",
        2,
        "policy",
        "SPEC 9.5 / C31",
        note="one evidence reviewer and one clinical reviewer, never the same identity",
    ),
    _spec("C32", "PRODUCTION_ACCEPTANCE_RERANK_WEIGHT", 0, "policy", "SPEC 9.9 / C32"),
    _spec("C33", "HASH_ALGORITHM", "sha256", "engineering", "SPEC 5.9 / C33"),
    _spec("C34", "OFFLINE_RANDOM_SEED", 42, "engineering", "SPEC 14.4 / C34"),
    _spec("C35", "PILOT_DATABASE", "postgresql>=16", "engineering", "SPEC 12.3 / C35"),
    _spec("C36", "MIN_TLS_VERSION", "1.2", "engineering", "SPEC 12.3 / C36"),
    _spec(
        "C37",
        "DECISION_POLICY_VERSION",
        None,
        "policy",
        "SPEC 8.6 / C37",
        note="no validated decision policy exists, so there are no operational risk bands",
    ),
    _spec("C38", "DQI_WINDOW_DAYS", 14, "policy", "SPEC 7.1 / C38"),
    _spec("C39", "DQI_RECENCY_HALF_LIFE_DAYS", 2, "policy", "SPEC 7.1 / C39"),
    _spec("C40", "DQI_ACCEPTED_DEFAULT_WEIGHT", 0.5, "policy", "SPEC 7.1 / C40"),
    _spec("C41", "DQI_CONSISTENCY_FLOOR", 0.5, "policy", "SPEC 7.1 / C41"),
    _spec("C42", "BASELINE_LOWER_QUANTILE", 0.05, "policy", "SPEC 8.3 / C42"),
    _spec("C43", "BASELINE_UPPER_QUANTILE", 0.95, "policy", "SPEC 8.3 / C43"),
    _spec("C44", "CHALLENGER_TIE_TOLERANCE", 1e-12, "engineering", "SPEC 8.4 / C44"),
    _spec("C45", "EVAL_BOOTSTRAP_REPLICATES", 2000, "engineering", "SPEC 14.4 / C45"),
    _spec("C46", "EVAL_INTERVAL_LEVEL", 0.90, "policy", "SPEC 14.4 / C46"),
    _spec("C47", "EVAL_MIN_VALID_BOOTSTRAP_FRACTION", 0.80, "policy", "SPEC 14.4 / C47"),
    _spec("C48", "GROUP_METRIC_MIN_SUBJECTS", 10, "policy", "SPEC 14.4 / C48"),
    _spec("C49", "GROUP_METRIC_MIN_POSITIVES", 5, "policy", "SPEC 14.4 / C49"),
    _spec("C50", "GROUP_METRIC_MIN_NEGATIVES", 5, "policy", "SPEC 14.4 / C50"),
)

CONSTANTS: dict[str, ConstantSpec] = {spec.constant_id: spec for spec in _REGISTRY}
CONSTANTS_BY_NAME: dict[str, ConstantSpec] = {spec.name: spec for spec in _REGISTRY}


def constant(constant_id: str) -> ConstantSpec:
    """Look up one registry entry, failing loudly on an unknown id."""

    try:
        return CONSTANTS[constant_id]
    except KeyError as error:  # pragma: no cover - defensive
        raise KeyError(f"unknown constant id {constant_id!r}") from error


def _value(constant_id: str) -> Any:
    return CONSTANTS[constant_id].value


# Module level names. Each one reads the registry so the literal exists once.
SPEC_VERSION: str = cast(str, _value("C01"))
API_PREFIX: str = cast(str, _value("C02"))
REFERENCE_TIMEZONE: str = cast(str, _value("C03"))
TARGET_HORIZON_HOURS: int = cast(int, _value("C04"))
OUTCOME_CAPTURE_LIMIT_HOURS: int = cast(int, _value("C05"))
DEFAULT_WINDOW_DAYS: int = cast(int, _value("C06"))
DEFAULT_PRIOR_PER_CATEGORY: int = cast(int, _value("C07"))
DEFAULT_LOWER_QUANTILE: float = cast(float, _value("C08"))
DEFAULT_LOWER_THRESHOLD: float = cast(float, _value("C09"))
DEFAULT_AUDIT_RATE: float = cast(float, _value("C10"))
FORM_HIGHLIGHTED_DEFAULT: int = cast(int, _value("C11"))
FORM_HIGHLIGHTED_LOW_COVERAGE: int = cast(int, _value("C12"))
LOW_COVERAGE_THRESHOLD: float = cast(float, _value("C13"))
STALENESS_CEILING_DAYS: int = cast(int, _value("C14"))
EXPLORATION_PERIOD: str = cast(str, _value("C15"))
CATEGORICAL_ANOMALY_PROBABILITY: float = cast(float, _value("C16"))
ROBUST_Z_ANOMALY: float = cast(float, _value("C17"))
BASELINE_WINDOW_DAYS: int = cast(int, _value("C18"))
BASELINE_MIN_OUTCOMES: int = cast(int, _value("C19"))
BASELINE_MAX_INTERVAL_WIDTH: float | None = cast("float | None", _value("C20"))
PERSONAL_DEVIATION_WINDOW_DAYS: int = cast(int, _value("C21"))
PERSONAL_MIN_OBSERVATIONS: int = cast(int, _value("C22"))
CHALLENGER_MAX_PREDICTORS: int = cast(int, _value("C23"))
CHALLENGER_L2_GRID: tuple[float, ...] = cast("tuple[float, ...]", _value("C24"))
RAG_LEXICAL_TOP_K: int = cast(int, _value("C25"))
RAG_DENSE_TOP_K: int = cast(int, _value("C26"))
RAG_RRF_K: int = cast(int, _value("C27"))
RAG_FINAL_CHUNKS: int = cast(int, _value("C28"))
RUNTIME_LLM_CALLS: int = cast(int, _value("C29"))
MAX_RUNTIME_STRATEGIES: int = cast(int, _value("C30"))
STRATEGY_REQUIRED_DISTINCT_REVIEWERS: int = cast(int, _value("C31"))
PRODUCTION_ACCEPTANCE_RERANK_WEIGHT: int = cast(int, _value("C32"))
HASH_ALGORITHM: str = cast(str, _value("C33"))
OFFLINE_RANDOM_SEED: int = cast(int, _value("C34"))
PILOT_DATABASE: str = cast(str, _value("C35"))
MIN_TLS_VERSION: str = cast(str, _value("C36"))
DECISION_POLICY_VERSION: str | None = cast("str | None", _value("C37"))
DQI_WINDOW_DAYS: int = cast(int, _value("C38"))
DQI_RECENCY_HALF_LIFE_DAYS: int = cast(int, _value("C39"))
DQI_ACCEPTED_DEFAULT_WEIGHT: float = cast(float, _value("C40"))
DQI_CONSISTENCY_FLOOR: float = cast(float, _value("C41"))
BASELINE_LOWER_QUANTILE: float = cast(float, _value("C42"))
BASELINE_UPPER_QUANTILE: float = cast(float, _value("C43"))
CHALLENGER_TIE_TOLERANCE: float = cast(float, _value("C44"))
EVAL_BOOTSTRAP_REPLICATES: int = cast(int, _value("C45"))
EVAL_INTERVAL_LEVEL: float = cast(float, _value("C46"))
EVAL_MIN_VALID_BOOTSTRAP_FRACTION: float = cast(float, _value("C47"))
GROUP_METRIC_MIN_SUBJECTS: int = cast(int, _value("C48"))
GROUP_METRIC_MIN_POSITIVES: int = cast(int, _value("C49"))
GROUP_METRIC_MIN_NEGATIVES: int = cast(int, _value("C50"))

__all__ = [
    "API_PREFIX",
    "BASELINE_LOWER_QUANTILE",
    "BASELINE_MAX_INTERVAL_WIDTH",
    "BASELINE_MIN_OUTCOMES",
    "BASELINE_UPPER_QUANTILE",
    "BASELINE_WINDOW_DAYS",
    "CATEGORICAL_ANOMALY_PROBABILITY",
    "CHALLENGER_L2_GRID",
    "CHALLENGER_MAX_PREDICTORS",
    "CHALLENGER_TIE_TOLERANCE",
    "CONSTANTS",
    "CONSTANTS_BY_NAME",
    "CONTRACT_VERSION",
    "DECISION_POLICY_VERSION",
    "DEFAULTS_ESTIMATOR_VERSION",
    "DEFAULT_AUDIT_RATE",
    "DEFAULT_LOWER_QUANTILE",
    "DEFAULT_LOWER_THRESHOLD",
    "DEFAULT_PRIOR_PER_CATEGORY",
    "DEFAULT_WINDOW_DAYS",
    "DQI_ACCEPTED_DEFAULT_WEIGHT",
    "DQI_CONSISTENCY_FLOOR",
    "DQI_RECENCY_HALF_LIFE_DAYS",
    "DQI_WINDOW_DAYS",
    "EVAL_BOOTSTRAP_REPLICATES",
    "EVAL_INTERVAL_LEVEL",
    "EVAL_MIN_VALID_BOOTSTRAP_FRACTION",
    "EXPLORATION_PERIOD",
    "FORM_HIGHLIGHTED_DEFAULT",
    "FORM_HIGHLIGHTED_LOW_COVERAGE",
    "FORM_POLICY_VERSION",
    "GROUP_METRIC_MIN_NEGATIVES",
    "GROUP_METRIC_MIN_POSITIVES",
    "GROUP_METRIC_MIN_SUBJECTS",
    "HASH_ALGORITHM",
    "LOW_COVERAGE_THRESHOLD",
    "MAX_RUNTIME_STRATEGIES",
    "MIN_TLS_VERSION",
    "OFFLINE_RANDOM_SEED",
    "OUTCOME_CAPTURE_LIMIT_HOURS",
    "PERSONAL_DEVIATION_WINDOW_DAYS",
    "PERSONAL_MIN_OBSERVATIONS",
    "PILOT_DATABASE",
    "PRODUCTION_ACCEPTANCE_RERANK_WEIGHT",
    "RAG_DENSE_TOP_K",
    "RAG_FINAL_CHUNKS",
    "RAG_LEXICAL_TOP_K",
    "RAG_RRF_K",
    "REFERENCE_TIMEZONE",
    "ROBUST_Z_ANOMALY",
    "RUNTIME_LLM_CALLS",
    "SCENARIO_BUILDER_VERSION",
    "SCENARIO_SCHEMA_VERSION",
    "SPEC_VERSION",
    "STALENESS_CEILING_DAYS",
    "STRATEGY_REQUIRED_DISTINCT_REVIEWERS",
    "TARGET_HORIZON_HOURS",
    "ConstantSpec",
    "DecisionClass",
    "constant",
]
