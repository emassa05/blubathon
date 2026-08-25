"""Dual-track prediction (SPEC 8).

Three tracks that never borrow each other's meaning:

`synthetic_reference_v021`
    A designed simulation over demo fixtures. It produces a `simulation_score`,
    never a probability, and refuses real subjects outright.
`real_personal_baseline_v1`
    The observed rate of the target among this subject's own previous primary
    episodes. It abstains with today's data, which is the correct answer.
`real_logit_challenger_v1`
    Two preregistered predictors on a baseline offset. It stays in shadow for
    all of v0.3 and reports `not_trainable_single_class` rather than fitting a
    model to one class.

There are no risk bands anywhere in this package: without a validated decision
policy, green, amber and red do not exist (SPEC 8.6, C37).
"""

from ml.prediction.baseline import (
    BASELINE_MODEL_VERSION,
    BaselineCandidate,
    BaselineEstimate,
    build_personal_baseline,
    eligible_outcomes,
    personal_rate,
)
from ml.prediction.challenger import (
    CHALLENGER_MODEL_VERSION,
    CHALLENGER_PROTOCOL_VERSION,
    ChallengerFit,
    ChallengerRow,
    ChallengerTrainingResult,
    LambdaSelection,
    PersonalRate,
    TrainabilityReport,
    assess_trainability,
    encode_predictor,
    fit_challenger,
    logit,
    negative_log_likelihood,
    personal_predictor_rate,
    select_penalty,
    sigmoid,
    train_challenger,
)
from ml.prediction.landmarks import (
    CHALLENGER_PREDICTORS,
    Landmark,
    RevealEvent,
    build_landmarks,
    estimable_rows,
    reveal_schedule,
    reveal_schedule_sha256,
)
from ml.prediction.synthetic_reference import (
    SYNTHETIC_MODEL_VERSION,
    SimulationArtifact,
    SimulationResult,
    guard_cohort,
    score_simulation,
)

__all__ = [
    "BASELINE_MODEL_VERSION",
    "CHALLENGER_MODEL_VERSION",
    "CHALLENGER_PREDICTORS",
    "CHALLENGER_PROTOCOL_VERSION",
    "SYNTHETIC_MODEL_VERSION",
    "BaselineCandidate",
    "BaselineEstimate",
    "ChallengerFit",
    "ChallengerRow",
    "ChallengerTrainingResult",
    "LambdaSelection",
    "Landmark",
    "PersonalRate",
    "RevealEvent",
    "SimulationArtifact",
    "SimulationResult",
    "TrainabilityReport",
    "assess_trainability",
    "build_landmarks",
    "build_personal_baseline",
    "eligible_outcomes",
    "encode_predictor",
    "estimable_rows",
    "fit_challenger",
    "guard_cohort",
    "logit",
    "negative_log_likelihood",
    "personal_predictor_rate",
    "personal_rate",
    "reveal_schedule",
    "reveal_schedule_sha256",
    "score_simulation",
    "select_penalty",
    "sigmoid",
    "train_challenger",
]
