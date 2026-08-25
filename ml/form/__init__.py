"""The adaptive form: quality, value of information, ordering and abstention.

Pure functions over already-loaded rows (CONVENTIONS 9.1). Nothing here reads a
database or a clock; the caller passes the history and the cutoff.
"""

from ml.form.anomaly import (
    CategoricalSurprise,
    FormAnomaly,
    RobustDeviation,
    compute_categorical_surprise,
    compute_robust_deviation,
    detect_form_anomaly,
)
from ml.form.plan import (
    FormPlan,
    PlannedQuestion,
    base_slots_for,
    build_form_plan,
    exploration_weekday,
    last_highlighted_dates,
)
from ml.form.quality import ENTRY_MODE_COVERAGE_WEIGHT, compute_dqi
from ml.form.scenario import ScenarioInputs, build_scenario
from ml.form.voi import (
    AnswerDistribution,
    ConditionalOutcomeModel,
    answer_distribution,
    binary_entropy,
    compute_predictive_voi,
    estimate_voi,
    voi_by_field,
)

__all__ = [
    "ENTRY_MODE_COVERAGE_WEIGHT",
    "AnswerDistribution",
    "CategoricalSurprise",
    "ConditionalOutcomeModel",
    "FormAnomaly",
    "FormPlan",
    "PlannedQuestion",
    "RobustDeviation",
    "ScenarioInputs",
    "answer_distribution",
    "base_slots_for",
    "binary_entropy",
    "build_form_plan",
    "build_scenario",
    "compute_categorical_surprise",
    "compute_dqi",
    "compute_predictive_voi",
    "compute_robust_deviation",
    "detect_form_anomaly",
    "estimate_voi",
    "exploration_weekday",
    "last_highlighted_dates",
    "voi_by_field",
]
