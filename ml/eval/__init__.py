"""Evaluation of a probability, with an honest answer when there is none (SPEC 14).

Development results only. Nothing here promotes a model, and nothing here reaches
`shadow_evaluated`: that state needs a preregistered prospective period on a
dataset separate from the one that chose `lambda`.
"""

from ml.eval.bootstrap import BootstrapInterval, cluster_bootstrap
from ml.eval.metrics import (
    CalibrationFit,
    auc_roc,
    average_precision,
    brier_score,
    calibration_fit,
    has_both_classes,
    logit,
)
from ml.eval.protocol import (
    EVALUATION_PROTOCOL_VERSION,
    OutOfFoldPrediction,
    OutOfFoldResult,
    evaluation_protocol,
    nested_out_of_fold,
)
from ml.eval.report import (
    ALERT_BUDGET_RECALL,
    GroupRows,
    abstention_breakdown,
    build_evaluation_report,
    completeness_metrics,
    core_metrics,
    decision_coverage,
    group_metrics,
    limitations,
    source_metrics,
)

__all__ = [
    "ALERT_BUDGET_RECALL",
    "EVALUATION_PROTOCOL_VERSION",
    "BootstrapInterval",
    "CalibrationFit",
    "GroupRows",
    "OutOfFoldPrediction",
    "OutOfFoldResult",
    "abstention_breakdown",
    "auc_roc",
    "average_precision",
    "brier_score",
    "build_evaluation_report",
    "calibration_fit",
    "cluster_bootstrap",
    "completeness_metrics",
    "core_metrics",
    "decision_coverage",
    "evaluation_protocol",
    "group_metrics",
    "has_both_classes",
    "limitations",
    "logit",
    "nested_out_of_fold",
    "source_metrics",
]
