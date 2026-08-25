"""Enums cerrados del contrato v0.3.

PROVISIONAL - PUERTO HACIA P1 (ver ``apps/api/contracts/__init__.py``).
Cada valor sale literalmente del SPEC; no se inventa ninguno.
"""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    """SPEC 5.4. Contexto de observación, no identidad ni canal."""

    HOME = "home"
    THERAPY = "therapy"
    SCHOOL = "school"


class EntryMode(StrEnum):
    """SPEC 5.5. Lo deriva el servidor; el cliente nunca lo envía."""

    MANUAL_NO_DEFAULT = "manual_no_default"
    AUDIT_MANUAL = "audit_manual"
    DEFAULT_ACCEPTED = "default_accepted"
    DEFAULT_EDITED = "default_edited"
    PROFESSIONAL_OBSERVED = "professional_observed"
    IMPORTED_OBSERVED = "imported_observed"
    EXPLICIT_UNKNOWN = "explicit_unknown"


class AnswerInteraction(StrEnum):
    """SPEC 11.3. Lo único que declara el cliente sobre una respuesta."""

    MANUAL = "manual"
    ACCEPT_DEFAULT = "accept_default"
    EDIT_DEFAULT = "edit_default"
    UNKNOWN = "unknown"


class DataOrigin(StrEnum):
    """SPEC 5.6. `FieldObservation.data_origin` y `PredictionOutput.input_data_origin`."""

    REAL = "real"
    SYNTHETIC = "synthetic"


class CohortKind(StrEnum):
    """SPEC 5.6. `Subject.cohort_kind`."""

    REAL_SUBJECT = "real_subject"
    DEMO_FIXTURE = "demo_fixture"


class DeploymentMode(StrEnum):
    """SPEC 5.6 y 12.3."""

    DEMO = "demo"
    PILOT = "pilot"


class SessionKind(StrEnum):
    """SPEC 5.5 precedencia 2 y SPEC 11.3."""

    CAREGIVER_DAILY = "caregiver_daily"
    PROFESSIONAL_OBSERVATION = "professional_observation"


class FormSessionStatus(StrEnum):
    """SPEC 16."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class PredictionStatus(StrEnum):
    """Resultado de la oportunidad canónica al cerrar la sesión (SPEC 4.2, 4.3)."""

    EPISODE_CREATED = "episode_created"
    EPISODE_LINKED = "episode_linked"
    TARGET_DEFINITION_UNAVAILABLE = "target_definition_unavailable"
    TARGET_DEFINITION_AMBIGUOUS = "target_definition_ambiguous"


class EpisodeRole(StrEnum):
    """SPEC 4.2. Solo `primary` entra a baseline y evaluación."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class EpisodeStatus(StrEnum):
    """SPEC 16."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TargetScope(StrEnum):
    """SPEC 4.3."""

    TENANT = "tenant"
    DEMO_FIXTURE = "demo_fixture"


class ApprovalStatus(StrEnum):
    """SPEC 4.3 para `TargetDefinitionVersion`."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class OutcomeValue(StrEnum):
    """SPEC 4.4. Lo que una persona reporta."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ResolutionStatus(StrEnum):
    """SPEC 4.4. Derivado, distinto del reporte."""

    PENDING = "pending"
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"


class TimingStatus(StrEnum):
    """SPEC 4.5."""

    EARLY = "early"
    ON_TIME = "on_time"
    LATE = "late"
    MISSING = "missing"


class OutcomeRequestStatus(StrEnum):
    """SPEC 4.4. Derivado de la resolución activa y del reloj; nunca se muta."""

    OPEN = "open"
    REPORTED = "reported"
    CONFLICTED = "conflicted"
    MISSING = "missing"


class IntakeChannel(StrEnum):
    """SPEC 4.4."""

    FORM = "form"
    IMPORT = "import"


class Role(StrEnum):
    """SPEC 13."""

    CAREGIVER = "caregiver"
    PROFESSIONAL = "professional"
    CLINICAL_REVIEWER = "clinical_reviewer"
    EVIDENCE_REVIEWER = "evidence_reviewer"
    PRIVACY_REVIEWER = "privacy_reviewer"
    MODEL_EVALUATOR = "model_evaluator"
    TENANT_ADMIN = "tenant_admin"
    AUDITOR = "auditor"


class AccreditationCapability(StrEnum):
    """SPEC 13.1 `ProfessionalAccreditation.capabilities`."""

    SUBJECT_CARE = "subject_care"
    TARGET_REVIEW = "target_review"
    STRATEGY_REVIEW = "strategy_review"
    EVIDENCE_REVIEW = "evidence_review"
    PRIVACY_REVIEW = "privacy_review"
    CATALOG_ACTIVATION = "catalog_activation"
    MODEL_EVALUATION = "model_evaluation"


class GrantCapability(StrEnum):
    """SPEC 13.1 `SubjectAccessGrant.capabilities`."""

    SUBJECT_READ = "subject_read"
    DAILY_OBSERVATION_WRITE = "daily_observation_write"
    FORM_SUBMIT = "form_submit"
    OUTCOME_REPORT = "outcome_report"
    RECOMMENDATION_REVIEW = "recommendation_review"
    EXECUTION_RECORD = "execution_record"
    EVALUATION_READ = "evaluation_read"


class ConsentPurpose(StrEnum):
    """SPEC 13.1 `Consent.purpose`."""

    OPERATIONAL_SUPPORT = "operational_support"
    SECONDARY_MODEL_USE = "secondary_model_use"
    AUTHORING_GENERALIZATION = "authoring_generalization"


class AuthorizationStatus(StrEnum):
    """SPEC 16. Consent, grant, accreditation y authoring authorization."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class IntendedUse(StrEnum):
    """SPEC 1.1."""

    SIMULATION_ONLY = "simulation_only"
    OPERATIONAL_SUPPORT = "operational_support"
    SHADOW_EVALUATION = "shadow_evaluation"
    AUTHORING_ONLY = "authoring_only"


class TrackId(StrEnum):
    """SPEC 8.1."""

    SYNTHETIC_REFERENCE = "synthetic_reference_v021"
    REAL_PERSONAL_BASELINE = "real_personal_baseline_v1"
    REAL_LOGIT_CHALLENGER = "real_logit_challenger_v1"


class PredictionOutputStatus(StrEnum):
    """SPEC 11.5."""

    OK = "ok"
    ABSTAINED = "abstained"
    UNAVAILABLE = "unavailable"


class EstimateKind(StrEnum):
    """SPEC 8.3 y 8.2. Nombra qué mide la salida, no cuánta confianza tiene."""

    PERSONAL_OBSERVED_EPISODE_RATE = "personal_observed_episode_rate"
    SIMULATION_DESIGNED_SCORE = "simulation_designed_score"
    SHADOW_SCORE = "shadow_score"


class VoiStatus(StrEnum):
    """SPEC 7.3."""

    AVAILABLE = "available"
    UNAVAILABLE_MODEL = "unavailable_model"
    UNAVAILABLE_FIELD_TYPE = "unavailable_field_type"
    UNAVAILABLE_PREDICTION = "unavailable_prediction"


class QuestionReason(StrEnum):
    """SPEC 6.9. Por qué el plan destacó una pregunta."""

    OUTCOME_PENDING = "outcome_pending"
    STALENESS = "staleness"
    EXPLORATION = "exploration"
    VOI = "voi"
    CANONICAL_ORDER = "canonical_order"
    TAIL = "tail"


class RuntimeStatus(StrEnum):
    """SPEC 10.1 `RecommendationInstance.runtime_status`."""

    MATCHED = "matched"
    ABSTAINED = "abstained"


class CatalogAvailability(StrEnum):
    """SPEC 9.6. Precedencia única de razones antes del runtime."""

    READY = "ready"
    CORPUS_NOT_READY = "corpus_not_ready"
    CLINICAL_REVIEW_UNAVAILABLE = "clinical_review_unavailable"
    CATALOG_SUSPENDED = "catalog_suspended"
    CATALOG_AMBIGUOUS = "catalog_ambiguous"
    CATALOG_NOT_READY = "catalog_not_ready"


class ReviewDecision(StrEnum):
    """SPEC 10.2."""

    APPROVED = "approved"
    REJECTED = "rejected"
    HUMAN_PLAN_SUBSTITUTED = "human_plan_substituted"
    NOT_APPLICABLE = "not_applicable"
    DEFERRED = "deferred"


class ExecutionStatus(StrEnum):
    """SPEC 10.3."""

    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNKNOWN = "unknown"


class RecommendationResponseStatus(StrEnum):
    """SPEC 11.6. Lo que ve quien consulta, ya filtrado por actor."""

    MATCHED = "matched"
    AWAITING_PROFESSIONAL_REVIEW = "awaiting_professional_review"
    ABSTAINED = "abstained"


class ItemType(StrEnum):
    """SPEC 11.6. Union servida al cuidador."""

    STRATEGY = "strategy"
    HUMAN_PLAN = "human_plan"


class NonActionableReason(StrEnum):
    """SPEC 10.2."""

    DEPENDENCY_SUSPENDED = "dependency_suspended"


class VersionStatus(StrEnum):
    """SPEC 9.5, 9.6 y 16 para estrategias, sets y catálogos."""

    DRAFT = "draft"
    EVIDENCE_REVIEWED = "evidence_reviewed"
    CLINICAL_REVIEWED = "clinical_reviewed"
    REVIEWED = "reviewed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class ReportEstimability(StrEnum):
    """SPEC 14.3. Una métrica sin soporte no devuelve cero."""

    ESTIMABLE = "estimable"
    NOT_ESTIMABLE = "not_estimable"
