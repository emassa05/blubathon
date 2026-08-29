"""Re-exports and the two response overlays still owned by the API layer."""

from __future__ import annotations

from apps.api.contracts.enums import OutcomeRequestState, OutcomeResolutionStatus
from packages.shared.domain.api import (
    AnswerItem,
    ChildHistoryDay,
    ChildHistoryOutcome,
    ChildHistoryPrediction,
    ChildHistoryRecommendation,
    ChildHistoryResponse,
    ChildListItem,
    ChildListResponse,
    ChildView,
    DefaultSuggestion,
    ErrorDetail,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    FormPlanRequest,
    FormPlanResponse,
    FormQuestion,
    FormSubmissionRequest,
    FormSubmissionResponse,
    NotificationEvent,
    OutcomeReportRequest,
    OutcomeReportResponse,
    OutcomeReportView,
    OutcomeRequestListResponse,
    OutcomeRequestView,
    OutcomeResolutionView,
    PredictionEpisodeResponse,
    PredictionOutputView,
    RecommendationCitation,
    RecommendationDecisionRequest,
    RecommendationDecisionResponse,
    RecommendationInstanceView,
    RecommendationListResponse,
    ReviewQueueResponse,
    TodayRecommendationResponse,
)
from packages.shared.domain.base import UtcDatetime


class PredictionEpisodeView(PredictionEpisodeResponse):
    prediction_at: UtcDatetime
    outcome_state: OutcomeRequestState | None = None
    resolution_status: OutcomeResolutionStatus | None = None


class OutcomeReportResponseView(OutcomeReportResponse):
    request_state: OutcomeRequestState


__all__ = [
    "AnswerItem",
    "ChildHistoryDay",
    "ChildHistoryOutcome",
    "ChildHistoryPrediction",
    "ChildHistoryRecommendation",
    "ChildHistoryResponse",
    "ChildListItem",
    "ChildListResponse",
    "ChildView",
    "DefaultSuggestion",
    "ErrorDetail",
    "ErrorResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "FormPlanRequest",
    "FormPlanResponse",
    "FormQuestion",
    "FormSubmissionRequest",
    "FormSubmissionResponse",
    "NotificationEvent",
    "OutcomeReportRequest",
    "OutcomeReportResponse",
    "OutcomeReportResponseView",
    "OutcomeReportView",
    "OutcomeRequestListResponse",
    "OutcomeRequestView",
    "OutcomeResolutionView",
    "PredictionEpisodeResponse",
    "PredictionEpisodeView",
    "PredictionOutputView",
    "RecommendationCitation",
    "RecommendationDecisionRequest",
    "RecommendationDecisionResponse",
    "RecommendationInstanceView",
    "RecommendationListResponse",
    "ReviewQueueResponse",
    "TodayRecommendationResponse",
]
