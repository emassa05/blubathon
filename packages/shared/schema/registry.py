"""The published contract surface.

Adding a model here publishes it: it gets a JSON Schema definition, a TypeScript
type and a Zod schema, and it becomes part of `schema_hash`. Removing one is a
breaking contract change.
"""

from __future__ import annotations

from types import MappingProxyType

from pydantic import BaseModel

from packages.shared.domain import api, evaluation, identity, observation, outcome, rag, review
from packages.shared.domain import prediction as prediction_models

SCHEMA_ARTIFACT = "contract_schema"

_PUBLISHED: tuple[type[BaseModel], ...] = (
    # Wire contracts for the eleven routes.
    api.ErrorDetail,
    api.ErrorResponse,
    api.DefaultSuggestion,
    api.FormQuestion,
    api.FormSessionCreateRequest,
    api.FormSessionResponse,
    api.FormAnswerRequest,
    api.FormSubmitResponse,
    api.PredictionOutputView,
    api.PredictionEpisodeResponse,
    api.OutcomeRequestView,
    api.OutcomeRequestListResponse,
    api.OutcomeReportRequest,
    api.OutcomeReportView,
    api.OutcomeResolutionView,
    api.OutcomeReportResponse,
    api.CitationView,
    api.StrategyItem,
    api.HumanPlanItem,
    api.RecommendationResponse,
    api.RecommendationInstanceView,
    api.RecommendationInboxResponse,
    api.RecommendationReviewRequest,
    api.RecommendationReviewResponse,
    api.StrategyExecutionRequest,
    api.StrategyExecutionResponse,
    api.EvaluationResponse,
    api.IdempotencyScope,
    # Domain rows P2 persists and P1 reads back.
    identity.Subject,
    identity.SubjectProfile,
    identity.Consent,
    identity.ProfessionalAccreditation,
    identity.SubjectAccessGrant,
    identity.AuthoringUseAuthorization,
    identity.AuthorizationContext,
    identity.OperationRequirement,
    identity.ConsentRevocationImpact,
    observation.SourceMapping,
    observation.FieldObservation,
    observation.PosteriorDefault,
    observation.DefaultPresentation,
    observation.QuestionPresentation,
    observation.FormSession,
    observation.AnswerSubmission,
    observation.DataQuality,
    prediction_models.TargetDefinitionVersion,
    prediction_models.TargetSelection,
    prediction_models.PredictionEpisode,
    prediction_models.FeatureSnapshot,
    prediction_models.PredictionOutput,
    prediction_models.VoiEstimate,
    outcome.OutcomeRequest,
    outcome.OutcomeReport,
    outcome.OutcomeResolution,
    outcome.OutcomeAdjudication,
    rag.DocumentVersion,
    rag.DocumentChunk,
    rag.AuthoringBuildManifest,
    rag.CorpusVersion,
    rag.AuthoringReview,
    rag.StrategyCitation,
    rag.StrategyClaim,
    rag.ScenarioV1,
    rag.ScenarioPredicate,
    rag.StrategyVersion,
    rag.RecommendationSetVersion,
    rag.CatalogVersion,
    rag.AuthoringRequestIntent,
    rag.AuthoringRequest,
    rag.ScenarioBuildResult,
    rag.RuntimeStrategyMatch,
    rag.RuntimeDecision,
    review.RecommendationInstance,
    review.HumanPlanVersion,
    review.RecommendationReview,
    review.StrategyExecution,
    evaluation.DatasetSnapshot,
    evaluation.ChallengerTrainingProtocolVersion,
    evaluation.EvaluationProtocolVersion,
    evaluation.TrainingRun,
    evaluation.ModelVersion,
    evaluation.MetricValue,
    evaluation.GroupMetric,
    evaluation.SourceMetric,
    evaluation.AbstentionBreakdown,
    evaluation.EvaluationReport,
    evaluation.ReleaseManifest,
)

PUBLISHED_MODELS: MappingProxyType[str, type[BaseModel]] = MappingProxyType(
    {model.__name__: model for model in _PUBLISHED}
)


def published_model(name: str) -> type[BaseModel]:
    """Look up one published model by its contract name."""

    try:
        return PUBLISHED_MODELS[name]
    except KeyError as error:
        raise KeyError(f"{name!r} is not part of the published contract") from error
