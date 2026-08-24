"""Code mirror of fixed values in SPEC v0.2.0."""

from __future__ import annotations

import math

SPEC_VERSION = "0.2.0"
MODEL_VERSION = "faro-0.2.0"
API_PREFIX = "/api/v1"
REFERENCE_TIMEZONE = "America/Santiago"
RANDOM_SEED = 42

RISK_MIN = 0.0
RISK_MAX = 1.0
RISK_API_DECIMALS = 4
BAND_AMBER = 0.15
BAND_RED = 0.35

ORDINAL_MIN = 1
ORDINAL_MAX = 5
SLEEP_HOURS_MIN = 0.0
SLEEP_HOURS_MAX = 16.0
NIGHT_AWAKENINGS_MIN = 0
NIGHT_AWAKENINGS_MAX = 15
DYSREGULATION_EVENTS_MIN = 0
DYSREGULATION_EVENTS_MAX = 20
TEXT_MAX_LENGTH = 500

BEHAVIOR_TAGS = (
    "calm",
    "irritable",
    "anxious",
    "withdrawn",
    "stereotypy",
    "aggression",
    "self_injury",
    "meltdown",
    "elopement",
    "other",
)
SOURCES = ("home", "therapy", "school")
CAPTURE_METHODS = ("form", "synthetic")
PROVENANCE_VALUES = ("observed", "confirmed", "assumed_stable", "unknown")
PROVENANCE_WEIGHTS = {
    "observed": 1.0,
    "confirmed": 1.0,
    "assumed_stable": 0.5,
    "unknown": 0.0,
}

NUMERIC_FIELDS = (
    "sleep_hours",
    "sleep_quality",
    "night_awakenings",
    "wake_state",
    "morning_support_need",
    "gi_status",
    "alertness",
    "dysregulation_events",
    "activity_participation",
    "social_interactions",
    "eating_status",
)
BOOLEAN_FIELDS = (
    "food_changes",
    "routine_changes",
    "relevant_event_flag",
    "crisis_occurred",
)
TEXT_FIELDS = (
    "observed_behavior_note",
    "relevant_events_note",
    "other_notes",
)
PROVENANCE_FIELDS = NUMERIC_FIELDS + BOOLEAN_FIELDS + TEXT_FIELDS + ("observed_behavior_tags",)
MODEL_INPUT_FIELDS = (
    "sleep_hours",
    "sleep_quality",
    "night_awakenings",
    "wake_state",
    "morning_support_need",
    "gi_status",
    "food_changes",
    "routine_changes",
    "alertness",
    "dysregulation_events",
    "activity_participation",
    "social_interactions",
    "eating_status",
    "relevant_event_flag",
)
ORDINAL_FIELDS = (
    "sleep_quality",
    "wake_state",
    "morning_support_need",
    "gi_status",
    "alertness",
    "activity_participation",
    "social_interactions",
    "eating_status",
)
FIELD_RANGES = {
    "sleep_hours": (SLEEP_HOURS_MIN, SLEEP_HOURS_MAX),
    "sleep_quality": (ORDINAL_MIN, ORDINAL_MAX),
    "night_awakenings": (NIGHT_AWAKENINGS_MIN, NIGHT_AWAKENINGS_MAX),
    "wake_state": (ORDINAL_MIN, ORDINAL_MAX),
    "morning_support_need": (ORDINAL_MIN, ORDINAL_MAX),
    "gi_status": (ORDINAL_MIN, ORDINAL_MAX),
    "alertness": (ORDINAL_MIN, ORDINAL_MAX),
    "dysregulation_events": (DYSREGULATION_EVENTS_MIN, DYSREGULATION_EVENTS_MAX),
    "activity_participation": (ORDINAL_MIN, ORDINAL_MAX),
    "social_interactions": (ORDINAL_MIN, ORDINAL_MAX),
    "eating_status": (ORDINAL_MIN, ORDINAL_MAX),
    "routine_changes": (RISK_MIN, RISK_MAX),
}

SOURCE_ALLOWED_FIELDS = {
    "home": frozenset(PROVENANCE_FIELDS),
    "therapy": frozenset(
        {
            "gi_status",
            "dysregulation_events",
            "activity_participation",
            "social_interactions",
            "observed_behavior_tags",
            "observed_behavior_note",
            "alertness",
            "crisis_occurred",
        }
    ),
    "school": frozenset(
        {
            "activity_participation",
            "social_interactions",
            "eating_status",
            "dysregulation_events",
            "observed_behavior_tags",
            "observed_behavior_note",
            "crisis_occurred",
        }
    ),
}

ICD_WINDOW_DAYS = 14
ICD_RECENCY_HALF_LIFE_DAYS = 2
ICD_RECENCY_LAMBDA = math.log(2) / ICD_RECENCY_HALF_LIFE_DAYS
ICD_CONSISTENCY_FLOOR = 0.5
ICD_WEIGHTS = {
    "sleep_hours": 1.0,
    "sleep_quality": 1.0,
    "night_awakenings": 0.8,
    "gi_status": 0.7,
    "routine_changes": 0.7,
    "wake_state": 0.6,
    "dysregulation_events": 0.6,
    "morning_support_need": 0.5,
    "alertness": 0.5,
    "social_interactions": 0.4,
    "activity_participation": 0.4,
    "eating_status": 0.3,
    "food_changes": 0.3,
    "relevant_event_flag": 0.3,
}
HIGH_WEIGHT_MIN = 0.5
HIGH_WEIGHT_FIELDS = frozenset(
    variable for variable, weight in ICD_WEIGHTS.items() if weight >= HIGH_WEIGHT_MIN
)

CONFIDENCE_HIGH_ICD = 0.70
CONFIDENCE_HIGH_WIDTH = 0.25
CONFIDENCE_MEDIUM_ICD = 0.45
CONFIDENCE_MEDIUM_WIDTH = 0.45
ABSTAIN_ICD = 0.35
ABSTAIN_WIDTH = 0.60
ABSTAIN_MIN_HISTORY_DAYS = 5

VOI_SAMPLES = 20
VOI_KAPPA = 0.15
VOI_PERSONAL_HISTORY_DAYS = 10
VOI_MIN_OBSERVATIONS = 5
VOI_PERSONAL_WINDOW_DAYS = 30
VOI_SUGGESTION_WINDOW_DAYS = 14
VOI_STALENESS_CEILING_DAYS = 7
VOI_EXPLORATION_MODULO = 7
VOI_ANOMALY_THRESHOLD = 2.0
VOI_DEFAULT_HIGHLIGHTED = 2
VOI_LOW_ICD_HIGHLIGHTED = 3
VOI_LOW_ICD_THRESHOLD = 0.5
VOI_MAX_REQUESTED_VARIABLES = 3

SYNTH_N_CHILDREN = 200
SYNTH_DAYS = 180
SYNTH_START_DATE = "2026-01-01"
SYNTH_TARGET_BASE_RATE = 0.10
SYNTH_BASE_RATE_MIN = 0.08
SYNTH_BASE_RATE_MAX = 0.12
SYNTH_COEFFICIENTS = {
    "intercept": -2.20,
    "sleep": 0.90,
    "awakenings": 0.50,
    "gi": 0.60,
    "routine": 0.60,
    "sensory": 0.40,
    "sleep_routine": 0.50,
    "gi_sensory": 0.35,
    "carryover": 0.30,
}
SYNTH_NOISE_STD = 0.70
SYNTH_SUSCEPTIBILITY_STD = 0.60
SYNTH_SLEEP_DEBT_WEIGHTS = (0.5, 0.3, 0.2)
SYNTH_GI_BURDEN_WEIGHTS = (0.6, 0.4)
SYNTH_ROUTINE_LOAD_WEIGHTS = (1.0, 0.5, 0.25)
SYNTH_SUPPORT_LOW_PROBABILITY = 0.60
SYNTH_HIGH_SUPPORT_NOISE_MULTIPLIER = 1.20
SYNTH_VERBAL_PROBABILITY = 0.70
SYNTH_CHRONIC_GI_PROBABILITY = 0.30
SYNTH_FEMALE_PROBABILITY = 0.50
SYNTH_SLEEP_NEED_MEAN = 9.0
SYNTH_SLEEP_NEED_STD = 1.0
SYNTH_SLEEP_NEED_MIN = 7.0
SYNTH_SLEEP_NEED_MAX = 11.0
SYNTH_PERSONAL_BASE_RATE_MIN = 0.05
SYNTH_PERSONAL_BASE_RATE_MAX = 0.20
SYNTH_NONVERBAL_GI_MULTIPLIER = 1.3
SYNTH_FEMALE_SIGNAL_FACTOR = 0.70
SYNTH_CAUSAL_ITERATIONS = 12
SYNTH_SLEEP_LOAD_FACTOR = 2.0
SYNTH_SLEEP_LOAD_DIVISOR = 3.0
SYNTH_SLEEP_NOISE_STD = 0.8
SYNTH_SLEEP_OBSERVED_MIN = 3.0
SYNTH_SLEEP_OBSERVED_MAX = 12.0
SYNTH_AWAKENINGS_BASE = 0.5
SYNTH_AWAKENINGS_LOAD_FACTOR = 1.5
SYNTH_EVENT_PROBABILITY_MIN = 0.10
SYNTH_EVENT_PROBABILITY_MAX = 0.15
SYNTH_MISSING_BASE = 0.25
SYNTH_MISSING_LOAD_FACTOR = 0.40
SYNTH_MISSING_LOAD_OFFSET = 0.5
SYNTH_MISSING_MAX = 0.85
SYNTH_MISSING_FORGETFUL_MULTIPLIER = 1.4
SYNTH_MISSING_SLEEP_MULTIPLIER = 0.6
SYNTH_THERAPY_DAYS_PER_WEEK = 2
SYNTH_DAYS_PER_WEEK = 7
SYNTH_WEEKEND_START = 5
SYNTH_THERAPY_WEEKDAYS = (1, 4)
SYNTH_GENERATOR_VERSION = "faro-synth-0.2.0"

SYNTH_GI_CHRONIC_PENALTY = 1.0
SYNTH_GI_NOISE_STD = 0.6
SYNTH_ALERTNESS_NOISE_STD = 0.8
SYNTH_STATE_NOISE_STD = 0.7
SYNTH_PARTICIPATION_NOISE_STD = 0.8
SYNTH_DYSREGULATION_LOAD_FACTOR = 2.0
SYNTH_DYSREGULATION_NOISE_MEAN = 0.5
SYNTH_DYSREGULATION_NOISE_STD = 1.0

BASELINE_AWAKENINGS_CENTER = 0.5
BASELINE_AWAKENINGS_SCALE = 1.5
BASELINE_GI_RANGE = 4.0
BASELINE_ALERTNESS_OPTIMAL = 3.0
BASELINE_ALERTNESS_SCALE = 2.0

FEATURE_MIN_OBSERVATIONS = 5
FEATURE_ROBUST_WINDOW_MIN_DAYS = 14
FEATURE_ROBUST_WINDOW_MAX_DAYS = 30
FEATURE_MAD_SCALE = 1.4826
FEATURE_LAGS = (1, 2)
FEATURE_ROLLING_WINDOWS = (3, 7)
FEATURE_TREND_WINDOW_DAYS = 7
FEATURE_MAHALANOBIS_REGULARIZATION = 1e-6

MODEL_OBJECTIVE = "binary"
MODEL_N_ESTIMATORS = 400
MODEL_LEARNING_RATE = 0.03
MODEL_NUM_LEAVES = 31
MODEL_MAX_DEPTH = 6
MODEL_MIN_CHILD_SAMPLES = 40
MODEL_SUBSAMPLE = 0.8
MODEL_COLSAMPLE_BYTREE = 0.8
MODEL_REG_LAMBDA = 1.0
MODEL_CLASS_WEIGHT = "balanced"
MODEL_EARLY_STOPPING_ROUNDS = 40
MODEL_ENSEMBLE_SIZE = 20
MODEL_INTERVAL_Z = 1.2816
MODEL_INTERVAL_COVERAGE = 0.80
MODEL_CONFORMAL_ALPHA = 0.10
MODEL_TRAIN_FRACTION = 0.60
MODEL_VALIDATION_FRACTION = 0.20
MODEL_TEST_FRACTION = 0.20
MODEL_TEMPORAL_HOLDOUT_DAYS = 30

NARRATIVE_TEMPERATURE = 0.2
NARRATIVE_MAX_ACTIONS = 3
NARRATIVE_MAX_EXPLANATION_WORDS = 60
NARRATIVE_MAX_RETRIES = 1
NARRATIVE_MAX_CANDIDATE_STRATEGIES = 4

EVALUATION_ECE_BINS = 10
EVALUATION_ALERT_BUDGET_DAYS = 7
ELICITATION_RESPONSE_INTERCEPT = 0.95
ELICITATION_RESPONSE_SLOPE = 0.045
ELICITATION_RESPONSE_MIN = 0.30
ELICITATION_RESPONSE_MAX = 0.95
ELICITATION_FIXED_FORM_FIELDS = 5
ELICITATION_FULL_FORM_FIELDS = 15
MISSPECIFICATION_BETA_MIN = 0.7
MISSPECIFICATION_BETA_MAX = 1.3
MISSPECIFICATION_CARRYOVERS = (0.15, 0.45)
MISSPECIFICATION_BASE_RATES = (0.06, 0.16)
MISSPECIFICATION_SEEDS = (142, 143, 144)
