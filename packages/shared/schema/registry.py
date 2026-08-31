"""The published contract surface.

Adding a model here publishes it: it gets a JSON Schema definition, a TypeScript
type and a Zod schema, and it becomes part of `schema_hash`. Removing one is a
breaking contract change.
"""

from __future__ import annotations

from types import MappingProxyType

from pydantic import BaseModel

from packages.shared.domain import api, evaluation, identity, observation, outcome, rag
from packages.shared.domain import prediction as prediction_models

SCHEMA_ARTIFACT = "contract_schema"

_PUBLISHED: tuple[type[BaseModel], ...] = (
    # Blubathon v0.4 HTTP and WebSocket contracts.
    api.ErrorDetail,
    api.ErrorResponse,
    api.DefaultSuggestion,
    api.FormQuestion,
    api.FormPlanRequest,
    api.FormPlanResponse,
    api.FormSubmissionRequest,
    api.FormSubmissionResponse,
    api.ChildView,
    api.ChildListResponse,
    api.ChildHistoryResponse,
    api.ChildHistoryDay,
    api.TodayRecommendationResponse,
    api.CalibrationBand,
    api.CalibrationResponse,
    api.PredictionOutputView,
    api.PredictionEpisodeResponse,
    api.OutcomeRequestView,
    api.OutcomeRequestListResponse,
    api.OutcomeReportRequest,
    api.OutcomeReportView,
    api.OutcomeResolutionView,
    api.OutcomeReportResponse,
    api.RecommendationInstanceView,
    api.RecommendationListResponse,
    api.FeedbackRequest,
    api.FeedbackResponse,
    api.RecommendationDecisionRequest,
    api.RecommendationDecisionResponse,
    api.ReviewQueueResponse,
    api.NotificationEvent,
    # Domain rows P2 persists and P1 reads back.
    identity.Subject,
    identity.SubjectProfile,
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
    rag.AuthoringRequestIntent,
    rag.AuthoringRequest,
    rag.ScenarioBuildResult,
    rag.RuntimeStrategyMatch,
    rag.RuntimeDecision,
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
