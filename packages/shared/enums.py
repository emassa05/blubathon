"""Closed vocabularies of the Faro contract.

Every value here comes from SPEC v0.3.0. Where the SPEC names a catalogue but
does not enumerate it (care modes, sensory and communication tags,
contraindications, behaviour tags, context tags), this module deliberately stops
at a token *shape* and leaves the contents to a versioned catalogue, because
SPEC 19 says a missing decision is recorded as a question, never invented.
"""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    """Observation context, not the actor and not a bibliographic source.

    `source_id` is reserved for corpus documents; `actor_id` records who
    reported and `source_mapping_id` which adapter was used (SPEC 5.4).
    """

    HOME = "home"
    THERAPY = "therapy"
    SCHOOL = "school"


class FieldCode(StrEnum):
    """The 19 daily observation fields of SPEC 5.2.

    `major_dysregulation_24h` is absent on purpose: it is an outcome, not a
    daily observation.
    """

    SLEEP_HOURS = "sleep_hours"
    SLEEP_QUALITY = "sleep_quality"
    NIGHT_AWAKENINGS = "night_awakenings"
    WAKE_STATE = "wake_state"
    MORNING_SUPPORT_NEED = "morning_support_need"
    GI_STATUS = "gi_status"
    MEDICATION_ADHERENCE = "medication_adherence"
    FOOD_CHANGES = "food_changes"
    ROUTINE_CHANGES = "routine_changes"
    ALERTNESS = "alertness"
    DYSREGULATION_EVENT_COUNT = "dysregulation_event_count"
    DAILY_REGULATION_STATE = "daily_regulation_state"
    ACTIVITY_PARTICIPATION = "activity_participation"
    SOCIAL_INTERACTIONS = "social_interactions"
    EATING_STATUS = "eating_status"
    ATTENDANCE_STATUS = "attendance_status"
    RELEVANT_EVENT_FLAG = "relevant_event_flag"
    BEHAVIOR_TAGS = "behavior_tags"
    NOTES = "notes"


class FieldKind(StrEnum):
    """How a field may be estimated, aggregated and compared (SPEC 5.3, 7.1)."""

    CONTINUOUS = "continuous"
    COUNT = "count"
    BOOLEAN = "boolean"
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    TAG_SET = "tag_set"
    TEXT = "text"


class SleepQuality(StrEnum):
    RESTORATIVE = "restorative"
    INTERRUPTED = "interrupted"
    SLEEP_ONSET_DIFFICULTY = "sleep_onset_difficulty"
    OTHER = "other"


class WakeState(StrEnum):
    CALM_HAPPY = "calm_happy"
    TIRED_SLEEPY = "tired_sleepy"
    IRRITABLE_CRYING = "irritable_crying"
    OTHER = "other"


class GiStatus(StrEnum):
    NORMAL = "normal"
    CONSTIPATION = "constipation"
    DIARRHEA = "diarrhea"
    OTHER = "other"


class MedicationAdherence(StrEnum):
    """`not_applicable` is a present answer, not a missing one (SPEC 7.1)."""

    TAKEN = "taken"
    MISSED = "missed"
    NOT_APPLICABLE = "not_applicable"


class Alertness(StrEnum):
    LOW = "low"
    CALM = "calm"
    OPTIMAL = "optimal"
    HIGH = "high"
    OTHER = "other"


class DailyRegulationState(StrEnum):
    EXCELLENT = "excellent"
    STABLE_WITH_SUPPORT = "stable_with_support"
    FREQUENT_DYSREGULATION = "frequent_dysregulation"
    OTHER = "other"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"


class EntryMode(StrEnum):
    """Derived by the server, never sent by a browser (SPEC 5.5)."""

    MANUAL_NO_DEFAULT = "manual_no_default"
    AUDIT_MANUAL = "audit_manual"
    DEFAULT_ACCEPTED = "default_accepted"
    DEFAULT_EDITED = "default_edited"
    PROFESSIONAL_OBSERVED = "professional_observed"
    IMPORTED_OBSERVED = "imported_observed"
    EXPLICIT_UNKNOWN = "explicit_unknown"


class AnswerInteraction(StrEnum):
    """What the client declares. The server derives `EntryMode` from it."""

    MANUAL = "manual"
    ACCEPT_DEFAULT = "accept_default"
    EDIT_DEFAULT = "edit_default"
    UNKNOWN = "unknown"


class DataOrigin(StrEnum):
    REAL = "real"
    SYNTHETIC = "synthetic"


class CohortKind(StrEnum):
    REAL_SUBJECT = "real_subject"
    DEMO_FIXTURE = "demo_fixture"


class DeploymentMode(StrEnum):
    DEMO = "demo"
    PILOT = "pilot"


class IntendedUse(StrEnum):
    SIMULATION_ONLY = "simulation_only"
    OPERATIONAL_SUPPORT = "operational_support"
    SHADOW_EVALUATION = "shadow_evaluation"
    AUTHORING_ONLY = "authoring_only"


class FormSessionKind(StrEnum):
    """A professional observation session shows no defaults (SPEC 5.5)."""

    CAREGIVER_DAILY = "caregiver_daily"
    PROFESSIONAL_OBSERVATION = "professional_observation"


class FormSessionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class SubmitStatus(StrEnum):
    """Only `episode_created` creates a snapshot, outputs and an outcome request."""

    EPISODE_CREATED = "episode_created"
    EPISODE_LINKED = "episode_linked"
    TARGET_DEFINITION_UNAVAILABLE = "target_definition_unavailable"


class EpisodeRole(StrEnum):
    """v0.3 creates exactly one role. Baseline and evaluation use only this one."""

    PRIMARY = "primary"


class PredictionEpisodeStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PredictionStatus(StrEnum):
    """Abstention is a valid HTTP 200 outcome (SPEC 2.11)."""

    OK = "ok"
    ABSTAINED = "abstained"
    UNAVAILABLE = "unavailable"


class TrackId(StrEnum):
    SYNTHETIC_REFERENCE_V021 = "synthetic_reference_v021"
    REAL_PERSONAL_BASELINE_V1 = "real_personal_baseline_v1"
    REAL_LOGIT_CHALLENGER_V1 = "real_logit_challenger_v1"


class EstimateKind(StrEnum):
    """What the number means, so a track cannot borrow another track's meaning."""

    PERSONAL_OBSERVED_EPISODE_RATE = "personal_observed_episode_rate"
    SIMULATION_SCORE = "simulation_score"
    SHADOW_CHALLENGER_SCORE = "shadow_challenger_score"


class IntervalMethod(StrEnum):
    BETA_POSTERIOR_QUANTILE = "beta_posterior_quantile"


class PredictionAbstentionReason(StrEnum):
    """Closed catalogue of why a track produced no visible estimate."""

    COLLECTING_DATA = "collecting_data"
    INSUFFICIENT_VERIFIED_OUTCOMES = "insufficient_verified_outcomes"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    CARE_MODE_HISTORY_UNAVAILABLE = "care_mode_history_unavailable"
    TARGET_DEFINITION_UNAVAILABLE = "target_definition_unavailable"
    TARGET_DEFINITION_AMBIGUOUS = "target_definition_ambiguous"
    MODEL_STATE_NOT_SHADOW = "model_state_not_shadow"
    PREDICTOR_MISSING = "predictor_missing"
    PERSONAL_PREDICTOR_HISTORY_INSUFFICIENT = "personal_predictor_history_insufficient"
    FEATURE_CONFLICT = "feature_conflict"
    UNSUPPORTED_MAPPING = "unsupported_mapping"
    CALIBRATION_FAILURE = "calibration_failure"
    COHORT_NOT_ELIGIBLE = "cohort_not_eligible"


class RecommendationAbstentionReason(StrEnum):
    """SPEC 9.6 derives exactly one reason, in this precedence order."""

    CORPUS_NOT_READY = "corpus_not_ready"
    CLINICAL_REVIEW_UNAVAILABLE = "clinical_review_unavailable"
    CATALOG_SUSPENDED = "catalog_suspended"
    CATALOG_AMBIGUOUS = "catalog_ambiguous"
    CATALOG_NOT_READY = "catalog_not_ready"
    NO_APPROVED_MATCH = "no_approved_match"
    SCENARIO_UNAVAILABLE_CONFLICT = "scenario_unavailable_conflict"


class CatalogReadiness(StrEnum):
    """The derived state P2 persists before calling the runtime (SPEC 9.6)."""

    CORPUS_NOT_READY = "corpus_not_ready"
    CLINICAL_REVIEW_UNAVAILABLE = "clinical_review_unavailable"
    CATALOG_SUSPENDED = "catalog_suspended"
    CATALOG_AMBIGUOUS = "catalog_ambiguous"
    CATALOG_NOT_READY = "catalog_not_ready"
    READY = "ready"


class VoiStatus(StrEnum):
    """Unavailable returns `voi_nats=null`, never zero (SPEC 7.3)."""

    AVAILABLE = "available"
    UNAVAILABLE_MODEL = "unavailable_model"
    UNAVAILABLE_FIELD_TYPE = "unavailable_field_type"
    UNAVAILABLE_PREDICTION = "unavailable_prediction"


class QuestionReason(StrEnum):
    """Why a field appears where it does in the plan (SPEC 6.9 order)."""

    OUTCOME_PENDING = "outcome_pending"
    STALENESS = "staleness"
    EXPLORATION = "exploration"
    VOI = "voi"
    CANONICAL_ORDER = "canonical_order"
    TAIL = "tail"


class FormAnomalyTrigger(StrEnum):
    """Any one of these opens the full queue (SPEC 6.11)."""

    RELEVANT_EVENT_FLAG = "relevant_event_flag"
    MEDICATION_MISSED = "medication_missed"
    FREQUENT_DYSREGULATION = "frequent_dysregulation"
    ALERTNESS_EXTREME = "alertness_extreme"
    CATEGORICAL_ANOMALY = "categorical_anomaly"
    ROBUST_Z_ANOMALY = "robust_z_anomaly"


class OutcomeReportValue(StrEnum):
    """A report is not a resolution (SPEC 4.4)."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class OutcomeResolutionStatus(StrEnum):
    PENDING = "pending"
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"


class TimingStatus(StrEnum):
    EARLY = "early"
    ON_TIME = "on_time"
    LATE = "late"
    MISSING = "missing"


class OutcomeRequestState(StrEnum):
    """Derived from the active resolution and the clock, never mutated."""

    OPEN = "open"
    REPORTED = "reported"
    CONFLICTED = "conflicted"
    MISSING = "missing"


class IntakeChannel(StrEnum):
    FORM = "form"
    IMPORT = "import"


class TargetScope(StrEnum):
    TENANT = "tenant"
    DEMO_FIXTURE = "demo_fixture"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    INDEXED = "indexed"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    EVIDENCE_REVIEWED = "evidence_reviewed"
    CLINICAL_REVIEWED = "clinical_reviewed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class CatalogStatus(StrEnum):
    """Shared by `RecommendationSetVersion` and `CatalogVersion` (SPEC 9.6)."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class RetrievalMode(StrEnum):
    HYBRID = "hybrid"
    LEXICAL_ONLY = "lexical_only"


class RuntimeStatus(StrEnum):
    MATCHED = "matched"
    ABSTAINED = "abstained"


class RecommendationResponseStatus(StrEnum):
    """What the caller sees; `awaiting_professional_review` hides pending items."""

    MATCHED = "matched"
    ABSTAINED = "abstained"
    AWAITING_PROFESSIONAL_REVIEW = "awaiting_professional_review"


class RecommendationItemType(StrEnum):
    STRATEGY = "strategy"
    HUMAN_PLAN = "human_plan"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    HUMAN_PLAN_SUBSTITUTED = "human_plan_substituted"
    NOT_APPLICABLE = "not_applicable"
    DEFERRED = "deferred"


class ReviewStatus(StrEnum):
    """Absence of an active review means pending; it is never stored (SPEC 10.1)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    HUMAN_PLAN_SUBSTITUTED = "human_plan_substituted"
    NOT_APPLICABLE = "not_applicable"
    DEFERRED = "deferred"


class ExecutionStatus(StrEnum):
    """Approval never proves application (SPEC 10.3)."""

    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNKNOWN = "unknown"


class NonActionableReason(StrEnum):
    DEPENDENCY_SUSPENDED = "dependency_suspended"


class Role(StrEnum):
    CAREGIVER = "caregiver"
    PROFESSIONAL = "professional"
    CLINICAL_REVIEWER = "clinical_reviewer"
    EVIDENCE_REVIEWER = "evidence_reviewer"
    PRIVACY_REVIEWER = "privacy_reviewer"
    MODEL_EVALUATOR = "model_evaluator"
    TENANT_ADMIN = "tenant_admin"
    AUDITOR = "auditor"


class ConsentPurpose(StrEnum):
    """Purposes are never substituted for one another (SPEC 13.1)."""

    OPERATIONAL_SUPPORT = "operational_support"
    SECONDARY_MODEL_USE = "secondary_model_use"
    AUTHORING_GENERALIZATION = "authoring_generalization"


class AccreditationCapability(StrEnum):
    SUBJECT_CARE = "subject_care"
    TARGET_REVIEW = "target_review"
    STRATEGY_REVIEW = "strategy_review"
    EVIDENCE_REVIEW = "evidence_review"
    PRIVACY_REVIEW = "privacy_review"
    CATALOG_ACTIVATION = "catalog_activation"
    MODEL_EVALUATION = "model_evaluation"


class GrantCapability(StrEnum):
    SUBJECT_READ = "subject_read"
    DAILY_OBSERVATION_WRITE = "daily_observation_write"
    FORM_SUBMIT = "form_submit"
    OUTCOME_REPORT = "outcome_report"
    RECOMMENDATION_REVIEW = "recommendation_review"
    EXECUTION_RECORD = "execution_record"
    EVALUATION_READ = "evaluation_read"


class AuthorizationStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthoringBasisType(StrEnum):
    CONSENT = "consent"
    INSTITUTIONAL_LEGAL_BASIS = "institutional_legal_basis"


class AuthoringScope(StrEnum):
    GENERALIZE_QUERY_ONLY = "generalize_query_only"


class AuthoringReviewObjectType(StrEnum):
    TARGET_DEFINITION = "target_definition"
    DOCUMENT = "document"
    STRATEGY = "strategy"
    RECOMMENDATION_SET = "recommendation_set"
    CATALOG = "catalog"


class AuthoringReviewKind(StrEnum):
    EVIDENCE = "evidence"
    CLINICAL = "clinical"
    PRIVACY = "privacy"
    CATALOG_ACTIVATION = "catalog_activation"


class AuthoringReviewDecision(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class AuthoringRequestStatus(StrEnum):
    OPEN = "open"
    EXPORTED = "exported"
    CLOSED = "closed"


class TrainingRunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    NOT_TRAINABLE = "not_trainable"
    FAILED = "failed"


class NotTrainableReason(StrEnum):
    SINGLE_CLASS = "not_trainable_single_class"
    INSUFFICIENT_SAMPLE_PLAN = "not_trainable_insufficient_sample_plan"
    CONVERGENCE_FAILURE = "not_trainable_convergence_failure"
    CONSENT_NOT_REAUTHORIZED = "not_trainable_consent_not_reauthorized"


class ModelState(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED_OFFLINE = "validated_offline"
    SHADOW = "shadow"
    SHADOW_EVALUATED = "shadow_evaluated"
    REJECTED = "rejected"
    SUSPENDED_FOR_CONSENT_REVIEW = "suspended_for_consent_review"
    RETIRED = "retired"


class EvaluationReportStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUSPENDED_FOR_CONSENT_REVIEW = "suspended_for_consent_review"
    RETIRED = "retired"


class MetricStatus(StrEnum):
    """A metric without support is `not_estimable`, never zero (CONVENTIONS 9.4)."""

    ESTIMATED = "estimated"
    NOT_ESTIMABLE = "not_estimable"


class ErrorCode(StrEnum):
    """Stable machine codes for the SPEC 11.7 error envelope.

    `forbidden` covers cross-tenant and same-tenant-without-grant alike: telling
    the caller which one it was would confirm that a subject exists somewhere
    else. Both are audited (SPEC 13.2).
    """

    VALIDATION_ERROR = "validation_error"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    REVISION_CONFLICT = "revision_conflict"
    RECOMMENDATION_DEPENDENCY_SUSPENDED = "recommendation_dependency_suspended"
    UNMAPPED_SOURCE_VALUE = "unmapped_source_value"
    TARGET_DEFINITION_AMBIGUOUS = "target_definition_ambiguous"
    ENTRY_MODE_NOT_DERIVABLE = "entry_mode_not_derivable"
    SYNTHETIC_ROW_IN_REAL_SNAPSHOT = "synthetic_row_in_real_snapshot"
    REAL_SUBJECT_NOT_ALLOWED_IN_DEMO = "real_subject_not_allowed_in_demo"
    INTERNAL_ERROR = "internal_error"
