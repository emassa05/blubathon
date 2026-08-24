"""Espejo en código del SPEC.v0.2.0.bak.md. Un cambio aquí exige un cambio allá.

CONVENTIONS §4: todo número 🔒 del SPEC vive una sola vez, aquí.
"""

# §0.9 — reproducibilidad total
RANDOM_SEED = 42

# §1 — versión de modelo / metadata
MODEL_VERSION = "faro-0.2.0"
SOURCE_ENUM = ("home", "therapy", "school")
CAPTURE_METHOD_ENUM = ("form", "synthetic", "voice")  # voice reservado, no implementado

# §2.1 — variables base y rangos
BEHAVIOR_TAG_ENUM = (
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
MAJOR_CRISIS_TAGS = ("meltdown", "aggression", "self_injury", "elopement")  # §3

FIELD_RANGES = {
    "sleep_hours": (0.0, 16.0),
    "sleep_quality": (1, 5),
    "night_awakenings": (0, 15),
    "wake_state": (1, 5),
    "morning_support_need": (1, 5),
    "gi_status": (1, 5),
    "alertness": (1, 5),
    "dysregulation_events": (0, 20),
    "activity_participation": (1, 5),
    "social_interactions": (1, 5),
    "eating_status": (1, 5),
}
ORDINAL_1_5_FIELDS = (
    "sleep_quality",
    "wake_state",
    "morning_support_need",
    "gi_status",
    "alertness",
    "activity_participation",
    "social_interactions",
    "eating_status",
)
NUMERIC_FIELDS = ("sleep_hours", "night_awakenings", "dysregulation_events")
BOOL_FIELDS = ("food_changes", "routine_changes", "relevant_event_flag", "crisis_occurred")

# §2.5 — procedencia por campo
PROVENANCE_ENUM = ("observed", "confirmed", "assumed_stable", "unknown")
PROVENANCE_WEIGHTS = {
    "observed": 1.0,
    "confirmed": 1.0,
    "assumed_stable": 0.5,
    "unknown": 0.0,
}

# §3 — target y horizonte
MIN_HISTORY_DAYS = 5  # §3, §6

# §4 — bandas de riesgo
BAND_AMBER, BAND_RED = 0.15, 0.35

# §4 — etiquetas ES de banda
BAND_LABELS_ES = {"verde": "riesgo bajo", "ambar": "riesgo medio", "rojo": "riesgo alto"}

# §5.1 — recency
RECENCY_HALF_LIFE_DAYS = 2  # lambda = ln(2)/2

# §5.2 — pesos de importancia w_v
IMPORTANCE_WEIGHTS = {
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
HIGH_WEIGHT = frozenset(v for v, w in IMPORTANCE_WEIGHTS.items() if w >= 0.5)

# §5.3 — etiqueta de confianza
CONFIDENCE_HIGH_ICD, CONFIDENCE_HIGH_WIDTH = 0.70, 0.25
CONFIDENCE_MED_ICD, CONFIDENCE_MED_WIDTH = 0.45, 0.45

# §6 — abstención
ABSTAIN_ICD = 0.35
ABSTAIN_WIDTH = 0.60
ABSTAIN_MIN_HISTORY_DAYS = 5
ABSTAIN_MESSAGE_TEMPLATE_ES = (
    "Todavía no tengo información suficiente para darte una estimación "
    "confiable. Me ayudaría saber: {variables}."
)

# §7.1 — VoI base
VOI_K = 20

# §7.2 — degradación por antigüedad
VOI_KAPPA = 0.15
VOI_PRIOR_MIN_HISTORY_DAYS = 10
VOI_PRIOR_MIN_OBSERVATIONS = 5

# §7.4 — formulario adaptativo
HIGHLIGHTED_SIZE_DEFAULT = 2
HIGHLIGHTED_SIZE_LOW_ICD = 3
HIGHLIGHTED_ICD_THRESHOLD = 0.5
FILTER_QUESTION_ES = "¿Hoy pasó algo distinto o fuera de lo común?"

# §7.5a — techo de antigüedad
STALENESS_CEILING_DAYS = 7

# §7.5b — gatillo por anomalía
ANOMALY_Z_THRESHOLD = 2.0

# §7.5c — cuota de exploración
EXPLORATION_MODULO = 7

# §7.6 — sugerencias
SUGGESTION_WINDOW_DAYS = 14
SUGGESTION_MIN_OBSERVATIONS = 5

# §8.1 — generador sintético
N_CHILDREN = 200
DAYS = 180
TARGET_BASE_RATE = 0.10

# §8.2 — coeficientes del generador causal
BETA_0 = -2.20
BETA_SLEEP = 0.90
BETA_AWAK = 0.50
BETA_GI = 0.60
BETA_ROUTINE = 0.60
BETA_SENSORY = 0.40
BETA_SLEEP_ROUTINE = 0.50
BETA_GI_SENSORY = 0.35
RHO_CARRYOVER = 0.30
SIGMA_NOISE = 0.70
THETA_SD = 0.60

# §8.4 — perfiles de niño
SUPPORT_LEVEL_HIGH_PROB = 0.40
VERBAL_PROB = 0.70
NON_VERBAL_GI_MULTIPLIER = 1.3
CHRONIC_GI_PROB = 0.30
SEX_FEMALE_PROB = 0.50
NEED_MEAN, NEED_SD = 9.0, 1.0
NEED_CLIP = (7.0, 11.0)
FEMALE_CAMOUFLAGE_FACTOR = 0.70  # atenúa señales *observadas*, no L

# §8.6 — missingness NMAR
P_MISS_BASE = 0.25
P_MISS_L_SLOPE = 0.40
P_MISS_L_CENTER = 0.5
P_MISS_CLIP = (0.0, 0.85)
P_MISS_FIELD_MULT = {
    "gi_status": 1.4,
    "social_interactions": 1.4,
    "night_awakenings": 1.4,
    "sleep_hours": 0.6,
    "sleep_quality": 0.6,
}

# §9.2 — LightGBM config fija
LGBM_PARAMS = dict(
    objective="binary",
    n_estimators=400,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=6,
    min_child_samples=40,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    class_weight="balanced",
    random_state=RANDOM_SEED,
)
LGBM_EARLY_STOPPING_PATIENCE = 40

# §9.3 — ensemble bootstrap / intervalo
ENSEMBLE_B = 20
ENSEMBLE_SEEDS = tuple(range(42, 62))
INTERVAL_Z = 1.2816  # 80%
CONFORMAL_ALPHA = 0.10

# §9.4 — splits
SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST = 0.60, 0.20, 0.20
TEMPORAL_HOLDOUT_DAYS = 30

# §10 — LLM
LLM_TEMPERATURE = 0.2
LLM_MAX_ACTIONS = 3
LLM_EXPLANATION_MAX_WORDS = 60
LLM_MAX_RETRIES = 1

# §12.1 — catálogo de estrategias (id -> label_es)
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

# §12.2 — mapeo driver -> estrategias candidatas
DRIVER_STRATEGY_MAP = {
    "sueño": ["advance_sleep", "co_regulation"],
    "rutina": ["visual_support", "anticipate_transition", "routine_predictability"],
    "GI": ["gi_comfort", "reduce_stimuli"],
    "sensorial/alerta": ["reduce_stimuli", "sensory_tools"],
    "desregulación": ["regulation_space", "co_regulation"],
    "colegio": ["anticipate_transition", "proactive_breaks"],
}
MAX_CANDIDATE_STRATEGIES = 4

# §12.3 — etiquetas ES de variables
VARIABLE_LABELS_ES = {
    "sleep_hours": "horas de sueño",
    "sleep_quality": "calidad del sueño",
    "night_awakenings": "despertares nocturnos",
    "wake_state": "estado al despertar",
    "morning_support_need": "apoyo matinal",
    "gi_status": "salud digestiva",
    "food_changes": "cambios en alimentación",
    "routine_changes": "cambios de rutina",
    "alertness": "estado de alerta",
    "dysregulation_events": "desregulaciones del día",
    "activity_participation": "participación en actividades",
    "social_interactions": "interacciones sociales",
    "eating_status": "alimentación",
    "relevant_event_flag": "evento relevante",
}

# §12.4 — prompt_es de micro-pregunta por variable
VARIABLE_PROMPTS_ES = {
    "sleep_hours": "¿Cuántas horas durmió anoche?",
    "sleep_quality": "¿Cómo durmió anoche?",
    "night_awakenings": "¿Cuántas veces se despertó en la noche?",
    "wake_state": "¿Cómo despertó hoy?",
    "morning_support_need": "¿Cuánto apoyo necesitó para iniciar el día?",
    "gi_status": "¿Tuvo molestias digestivas hoy?",
    "routine_changes": "¿Hubo algún cambio en su rutina?",
    "alertness": "¿Cómo estuvo su estado de alerta hoy?",
    "social_interactions": "¿Cómo fueron sus interacciones sociales?",
    "activity_participation": "¿Cómo participó en sus actividades?",
    "eating_status": "¿Cómo estuvo su alimentación hoy?",
    "food_changes": "¿Hubo cambios en lo que comió?",
    "dysregulation_events": "¿Tuvo episodios de desregulación hoy? ¿Cuántos?",
    "relevant_event_flag": "¿Hoy pasó algo distinto o fuera de lo común?",
}

# §12.5 — anclas verbales de escalas ordinales (5 = valor de la clave)
VERBAL_ANCHORS = {
    "sleep_quality": {
        1: "Pésima — casi no durmió, muchos despertares",
        2: "Mala — durmió poco o muy inquieto",
        3: "Regular — durmió, pero con interrupciones",
        4: "Buena — durmió bien, alguna interrupción menor",
        5: "Excelente — durmió de corrido y despertó descansado",
    },
    "wake_state": {
        1: "Muy desregulado — despertó llorando o muy alterado",
        2: "Desregulado — despertó irritable o muy sensible",
        3: "Neutro — ni bien ni mal",
        4: "Tranquilo — despertó bien, con buena disposición",
        5: "Muy tranquilo — despertó descansado y regulado",
    },
    "morning_support_need": {
        1: "Autónomo — hizo su rutina solo",
        2: "Poco apoyo — recordatorios puntuales",
        3: "Apoyo moderado — acompañamiento en varias partes",
        4: "Mucho apoyo — hubo que guiar casi todo",
        5: "Apoyo total — no logró iniciar el día sin ayuda constante",
    },
    "gi_status": {
        1: "Muy mal — dolor evidente, vómitos o diarrea",
        2: "Mal — molestias claras (dolor, estitiquez, náuseas)",
        3: "Regular — algo de molestia, poco clara",
        4: "Bien — sin molestias notorias",
        5: "Muy bien — digestión normal, sin señales",
    },
    "alertness": {
        1: "Muy apagado — somnoliento, sin energía",
        2: "Bajo — más lento o desconectado de lo habitual",
        3: "Adecuado — alerta y disponible",
        4: "Acelerado — más inquieto o activado de lo habitual",
        5: "Muy acelerado — muy activado, difícil de calmar",
    },
    "activity_participation": {
        1: "No participó",
        2: "Participó muy poco, con mucha resistencia",
        3: "Participó a ratos",
        4: "Participó bien la mayor parte del tiempo",
        5: "Participó plenamente",
    },
    "social_interactions": {
        1: "Muy difíciles — conflictos o retraimiento marcado",
        2: "Difíciles — le costó relacionarse",
        3: "Neutras — sin nada destacable",
        4: "Buenas — interactuó bien",
        5: "Muy buenas — disfrutó el contacto con otros",
    },
    "eating_status": {
        1: "Casi no comió",
        2: "Comió poco o rechazó comidas",
        3: "Comió algo menos de lo habitual",
        4: "Comió bien",
        5: "Comió muy bien, sin dificultad",
    },
}

# §13 — evaluación / ablaciones
ALERT_BUDGET_PER_CHILD_WEEK = 1

# §13.1 — ablación de política de elicitación (modelo de adherencia)
ADHERENCE_BASE = 0.95
ADHERENCE_SLOPE = 0.045
ADHERENCE_CLIP = (0.30, 0.95)
STALE_CHANGE_THRESHOLD_POINTS = 2

# §13.2 — mala especificación
MISSPEC_BETA_RANGE = (0.7, 1.3)
MISSPEC_RHO_VALUES = (0.15, 0.45)
MISSPEC_BASE_RATE_VALUES = (0.06, 0.16)
MISSPEC_SEEDS = (142, 143, 144)
