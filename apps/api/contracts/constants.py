"""Registro de constantes normativas del SPEC (C01-C50).

PROVISIONAL - PUERTO HACIA P1.

`CONVENTIONS 6` sitúa las constantes contractuales en
``packages/shared/constants.py``, propiedad de P1. Ese módulo todavía no existe
en la versión 0.3.0 del contrato, así que P2 declara aquí los mismos valores del
registro `SPEC 15` para poder construir API, store y UI en paralelo.

Cuando P1 publique `packages.shared.constants`, este archivo se reemplaza por un
re-export de aquel módulo. Ningún otro archivo de `apps/` repite un literal del
registro: todos importan desde aquí (`CONVENTIONS 7`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

DecisionClass = Literal["mathematical", "evidence", "policy", "engineering"]


@dataclass(frozen=True, slots=True)
class ConstantSpec:
    """Un valor normativo con su clase de decisión y su referencia al SPEC."""

    value: Any
    decision_class: DecisionClass
    spec_ref: str


REGISTRY: dict[str, ConstantSpec] = {
    "SPEC_VERSION": ConstantSpec("0.3.0", "engineering", "SPEC 15 / C01"),
    "API_PREFIX": ConstantSpec("/api/v1", "engineering", "SPEC 15 / C02"),
    "REFERENCE_TIMEZONE": ConstantSpec("America/Santiago", "engineering", "SPEC 15 / C03"),
    "TARGET_HORIZON_HOURS": ConstantSpec(24, "policy", "SPEC 4.1 / C04"),
    "OUTCOME_CAPTURE_LIMIT_HOURS": ConstantSpec(48, "policy", "SPEC 4.1 / C05"),
    "DEFAULT_WINDOW_DAYS": ConstantSpec(60, "policy", "SPEC 6.2 / C06"),
    "DEFAULT_PRIOR_PER_CATEGORY": ConstantSpec(1, "policy", "SPEC 6.3 / C07"),
    "DEFAULT_LOWER_QUANTILE": ConstantSpec(0.05, "policy", "SPEC 6.3 / C08"),
    "DEFAULT_LOWER_THRESHOLD": ConstantSpec(0.70, "policy", "SPEC 6.6 / C09"),
    "DEFAULT_AUDIT_RATE": ConstantSpec(0.10, "policy", "SPEC 6.8 / C10"),
    "FORM_HIGHLIGHTED_DEFAULT": ConstantSpec(2, "policy", "SPEC 6.9 / C11"),
    "FORM_HIGHLIGHTED_LOW_COVERAGE": ConstantSpec(3, "policy", "SPEC 6.9 / C12"),
    "LOW_COVERAGE_THRESHOLD": ConstantSpec(0.50, "policy", "SPEC 6.9 / C13"),
    "STALENESS_CEILING_DAYS": ConstantSpec(7, "policy", "SPEC 6.10 / C14"),
    "EXPLORATION_PERIOD": ConstantSpec(1, "policy", "SPEC 6.10 / C15"),
    "CATEGORICAL_ANOMALY_PROBABILITY": ConstantSpec(0.05, "policy", "SPEC 6.11 / C16"),
    "ROBUST_Z_ANOMALY": ConstantSpec(2.0, "policy", "SPEC 6.11 / C17"),
    "BASELINE_WINDOW_DAYS": ConstantSpec(60, "policy", "SPEC 8.3 / C18"),
    "BASELINE_MIN_OUTCOMES": ConstantSpec(5, "policy", "SPEC 8.5 / C19"),
    "BASELINE_MAX_INTERVAL_WIDTH": ConstantSpec(None, "policy", "SPEC 8.5 / C20"),
    "PERSONAL_DEVIATION_WINDOW_DAYS": ConstantSpec(30, "policy", "SPEC 6.11 / C21"),
    "PERSONAL_MIN_OBSERVATIONS": ConstantSpec(5, "policy", "SPEC 6.11 / C22"),
    "CHALLENGER_MAX_PREDICTORS": ConstantSpec(2, "policy", "SPEC 8.4 / C23"),
    "CHALLENGER_L2_GRID": ConstantSpec((0.01, 0.1, 1, 10, 100), "engineering", "SPEC 8.4 / C24"),
    "RAG_LEXICAL_TOP_K": ConstantSpec(20, "engineering", "SPEC 9.4 / C25"),
    "RAG_DENSE_TOP_K": ConstantSpec(20, "engineering", "SPEC 9.4 / C26"),
    "RAG_RRF_K": ConstantSpec(60, "engineering", "SPEC 9.4 / C27"),
    "RAG_FINAL_CHUNKS": ConstantSpec(8, "engineering", "SPEC 9.4 / C28"),
    "RUNTIME_LLM_CALLS": ConstantSpec(0, "policy", "SPEC 9.1 / C29"),
    "MAX_RUNTIME_STRATEGIES": ConstantSpec(3, "policy", "SPEC 9.8 / C30"),
    "STRATEGY_REQUIRED_DISTINCT_REVIEWERS": ConstantSpec(2, "policy", "SPEC 9.5 / C31"),
    "PRODUCTION_ACCEPTANCE_RERANK_WEIGHT": ConstantSpec(0, "policy", "SPEC 9.9 / C32"),
    "HASH_ALGORITHM": ConstantSpec("sha256", "engineering", "SPEC 5.9 / C33"),
    "OFFLINE_RANDOM_SEED": ConstantSpec(42, "engineering", "SPEC 15 / C34"),
    "PILOT_DATABASE": ConstantSpec("postgresql", "engineering", "SPEC 12.3 / C35"),
    "MIN_TLS_VERSION": ConstantSpec("1.2", "engineering", "SPEC 12.3 / C36"),
    "DECISION_POLICY_VERSION": ConstantSpec(None, "policy", "SPEC 8.6 / C37"),
    "DQI_WINDOW_DAYS": ConstantSpec(14, "policy", "SPEC 7.1 / C38"),
    "DQI_RECENCY_HALF_LIFE_DAYS": ConstantSpec(2, "policy", "SPEC 7.1 / C39"),
    "DQI_ACCEPTED_DEFAULT_WEIGHT": ConstantSpec(0.5, "policy", "SPEC 7.1 / C40"),
    "DQI_CONSISTENCY_FLOOR": ConstantSpec(0.5, "policy", "SPEC 7.1 / C41"),
    "BASELINE_LOWER_QUANTILE": ConstantSpec(0.05, "policy", "SPEC 8.3 / C42"),
    "BASELINE_UPPER_QUANTILE": ConstantSpec(0.95, "policy", "SPEC 8.3 / C43"),
    "CHALLENGER_TIE_TOLERANCE": ConstantSpec(1e-12, "engineering", "SPEC 8.4 / C44"),
    "EVAL_BOOTSTRAP_REPLICATES": ConstantSpec(2000, "engineering", "SPEC 14.4 / C45"),
    "EVAL_INTERVAL_LEVEL": ConstantSpec(0.90, "policy", "SPEC 14.4 / C46"),
    "EVAL_MIN_VALID_BOOTSTRAP_FRACTION": ConstantSpec(0.80, "policy", "SPEC 14.4 / C47"),
    "GROUP_METRIC_MIN_SUBJECTS": ConstantSpec(10, "policy", "SPEC 14.4 / C48"),
    "GROUP_METRIC_MIN_POSITIVES": ConstantSpec(5, "policy", "SPEC 14.4 / C49"),
    "GROUP_METRIC_MIN_NEGATIVES": ConstantSpec(5, "policy", "SPEC 14.4 / C50"),
}


def constant(name: str) -> Any:
    """Único acceso a un valor del registro. Un nombre desconocido falla cerrado."""
    try:
        return REGISTRY[name].value
    except KeyError as error:  # pragma: no cover - defensivo
        raise KeyError(f"constante no registrada en SPEC 15: {name}") from error


SPEC_VERSION: str = constant("SPEC_VERSION")
API_PREFIX: str = constant("API_PREFIX")
REFERENCE_TIMEZONE: str = constant("REFERENCE_TIMEZONE")
TARGET_HORIZON_HOURS: int = constant("TARGET_HORIZON_HOURS")
OUTCOME_CAPTURE_LIMIT_HOURS: int = constant("OUTCOME_CAPTURE_LIMIT_HOURS")
DEFAULT_LOWER_THRESHOLD: float = constant("DEFAULT_LOWER_THRESHOLD")
DEFAULT_AUDIT_RATE: float = constant("DEFAULT_AUDIT_RATE")
FORM_HIGHLIGHTED_DEFAULT: int = constant("FORM_HIGHLIGHTED_DEFAULT")
FORM_HIGHLIGHTED_LOW_COVERAGE: int = constant("FORM_HIGHLIGHTED_LOW_COVERAGE")
LOW_COVERAGE_THRESHOLD: float = constant("LOW_COVERAGE_THRESHOLD")
STALENESS_CEILING_DAYS: int = constant("STALENESS_CEILING_DAYS")
BASELINE_MIN_OUTCOMES: int = constant("BASELINE_MIN_OUTCOMES")
MAX_RUNTIME_STRATEGIES: int = constant("MAX_RUNTIME_STRATEGIES")
DECISION_POLICY_VERSION: str | None = constant("DECISION_POLICY_VERSION")
HASH_ALGORITHM: str = constant("HASH_ALGORITHM")
PILOT_DATABASE: str = constant("PILOT_DATABASE")

# Versiones de política que el servidor estampa en lo que persiste. No son
# constantes numéricas del registro: identifican qué reglas se aplicaron.
FORM_POLICY_VERSION = "form-0.3.0"
DEFAULTS_ESTIMATOR_VERSION = "defaults-0.3.0"
SCENARIO_SCHEMA_VERSION = "scenario-1"
BEHAVIOR_TAG_CATALOG_VERSION = "behavior-tags-0.3.0"
