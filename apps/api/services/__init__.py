"""Servicios de aplicación (CONVENTIONS 12.1)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.api.services.base import CommandResult, IdempotentRequest, Services
from apps.api.services.episodes import EpisodeService
from apps.api.services.evaluation import EvaluationService
from apps.api.services.form_sessions import FormSessionService
from apps.api.services.outcomes import OutcomeService
from apps.api.services.recommendations import RecommendationService


@dataclass(frozen=True, slots=True)
class ServiceRegistry:
    core: Services
    form_sessions: FormSessionService
    episodes: EpisodeService
    outcomes: OutcomeService
    recommendations: RecommendationService
    evaluation: EvaluationService


def build_registry(core: Services) -> ServiceRegistry:
    return ServiceRegistry(
        core=core,
        form_sessions=FormSessionService(core),
        episodes=EpisodeService(core),
        outcomes=OutcomeService(core),
        recommendations=RecommendationService(core),
        evaluation=EvaluationService(core),
    )


__all__ = [
    "CommandResult",
    "EpisodeService",
    "EvaluationService",
    "FormSessionService",
    "IdempotentRequest",
    "OutcomeService",
    "RecommendationService",
    "ServiceRegistry",
    "Services",
    "build_registry",
]
