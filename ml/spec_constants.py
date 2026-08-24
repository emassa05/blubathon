"""Code mirror of fixed values in SPEC v0.2.0."""

from __future__ import annotations

import math

SPEC_VERSION = "0.2.1"
MODEL_VERSION = "faro-0.2.1"
API_PREFIX = "/api/v1"
REFERENCE_TIMEZONE = "America/Santiago"
RANDOM_SEED = 42
PREDICTION_HORIZON_DAYS = 1

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

# SPEC 2.1 field 16 (added in 0.2.1, see SPEC 14.1). Bluba records medication
# adherence as a three-state answer: taken, missed, or no medication prescribed.
# "not_applicable" is a real answer and must not collapse into the null that
# means nobody replied, so the model receives a nominal code plus its
# *_missing flag rather than an ordinal.
MEDICATION_ADHERENCE_VALUES = ("taken", "missed", "not_applicable")
MEDICATION_ADHERENCE_CODES = {"missed": 0, "taken": 1, "not_applicable": 2}
MEDICATION_CODE_MIN = 0
MEDICATION_CODE_MAX = 2

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
CATEGORICAL_FIELDS = ("medication_adherence",)
TEXT_FIELDS = (
    "observed_behavior_note",
    "relevant_events_note",
    "other_notes",
)
PROVENANCE_FIELDS = (
    NUMERIC_FIELDS + BOOLEAN_FIELDS + CATEGORICAL_FIELDS + TEXT_FIELDS + ("observed_behavior_tags",)
)
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
    "medication_adherence",
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
    "food_changes": (RISK_MIN, RISK_MAX),
    "routine_changes": (RISK_MIN, RISK_MAX),
    "relevant_event_flag": (RISK_MIN, RISK_MAX),
    "medication_adherence": (MEDICATION_CODE_MIN, MEDICATION_CODE_MAX),
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
            "medication_adherence",
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
    "medication_adherence": 0.6,
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
    "medication": 0.45,
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
FEATURE_ZERO_MAD_SCALE = 1.0
FEATURE_WEEKDAY_MIN_OBSERVATIONS = 2
FEATURE_LAGS = (1, 2)
FEATURE_ROLLING_WINDOWS = (3, 7)
FEATURE_TREND_WINDOW_DAYS = 7
FEATURE_MAHALANOBIS_REGULARIZATION = 1e-6
FEATURE_LAG_FIELDS = (
    "sleep_hours",
    "sleep_quality",
    "night_awakenings",
    "gi_status",
    "routine_changes",
)

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
MODEL_ENSEMBLE_SEEDS = tuple(range(RANDOM_SEED, RANDOM_SEED + MODEL_ENSEMBLE_SIZE))
MODEL_INTERVAL_Z = 1.2816
MODEL_INTERVAL_COVERAGE = 0.80
MODEL_CONFORMAL_ALPHA = 0.10
MODEL_CONFORMAL_CONFIDENCE = 1.0 - MODEL_CONFORMAL_ALPHA
MODEL_MIN_CONFORMAL_SAMPLES = int(1.0 / MODEL_CONFORMAL_ALPHA)
MODEL_TRAIN_FRACTION = 0.60
MODEL_VALIDATION_FRACTION = 0.20
MODEL_TEST_FRACTION = 0.20
MODEL_CALIBRATION_FRACTION = 0.50
MODEL_TEMPORAL_HOLDOUT_DAYS = 30
MODEL_MIN_SPLIT_CHILDREN = 5

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

# SPEC 12.1 — closed strategy catalogue. The LLM may only pick from this list.
STRATEGIES = {
    "visual_support": "Apoyos visuales / agenda anticipada",
    "reduce_stimuli": "Reducir estímulos sensoriales",
    "advance_sleep": "Proteger / adelantar la rutina de sueño",
    "anticipate_transition": "Anticipar verbalmente las transiciones",
    "regulation_space": "Ofrecer un espacio de regulación",
    "sensory_tools": "Herramientas sensoriales (audífonos, presión)",
    "routine_predictability": "Reforzar la predictibilidad de la rutina",
    "gi_comfort": "Atender molestias físicas / GI",
    "proactive_breaks": "Pausas proactivas estructuradas",
    "co_regulation": "Co-regulación y presencia calmada",
}

# SPEC 12.2 — driver to candidate strategies.
DRIVER_STRATEGY_MAP = {
    "sueño": ("advance_sleep", "co_regulation"),
    "rutina": ("visual_support", "anticipate_transition", "routine_predictability"),
    "GI": ("gi_comfort", "reduce_stimuli"),
    "sensorial/alerta": ("reduce_stimuli", "sensory_tools"),
    "desregulación": ("regulation_space", "co_regulation"),
    "colegio": ("anticipate_transition", "proactive_breaks"),
    # Added with medication_adherence (SPEC 14.1): a missed dose is a physical
    # driver, so it routes to the same comfort and co-regulation supports.
    "medicación": ("gi_comfort", "co_regulation"),
}

# SPEC 3 — a major dysregulation event is what crisis_occurred records.
MAJOR_CRISIS_TAGS = ("meltdown", "aggression", "self_injury", "elopement")

# SPEC 13 — one alert per child per week is the budget the recall curve reports.
EVALUATION_ALERT_BUDGET_PER_CHILD = 1

# SPEC 13.1 — questions each elicitation policy shows per day.
ELICITATION_POLICY_QUESTIONS = {"A": 15, "B": 3, "C": 5, "D": 2}
# SPEC 13.1 — a HIGH_WEIGHT variable that moved this much without being asked.
STALE_CHANGE_THRESHOLD_POINTS = 2.0

# SPEC 8.4 extension (0.2.1): Bluba records medication adherence, so the
# generator must produce it or the model has nothing to learn from. Roughly one
# child in three has a prescription, and a missed dose raises the day's load
# about as much as a change of routine.
SYNTH_MEDICATED_PROBABILITY = 0.35
SYNTH_MEDICATION_MISS_PROBABILITY = 0.12
