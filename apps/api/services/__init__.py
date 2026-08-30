"""Application service registry."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from apps.api.services.base import Services
from apps.api.services.calibration import CalibrationService
from apps.api.services.children import ChildService
from apps.api.services.episodes import EpisodeService
from apps.api.services.outcomes import OutcomeService
from apps.api.services.submissions import SubmissionService


@dataclass(frozen=True, slots=True)
class ServiceRegistry:
    core: Services
    children: ChildService
    calibration: CalibrationService
    submissions: SubmissionService
    episodes: EpisodeService
    outcomes: OutcomeService
    recommendations: Any


def build_registry(core: Services) -> ServiceRegistry:
    recommendation_service = import_module(
        "apps.api.services.recommendations"
    ).RecommendationService
    return ServiceRegistry(
        core=core,
        children=ChildService(core),
        calibration=CalibrationService(core),
        submissions=SubmissionService(core),
        episodes=EpisodeService(core),
        outcomes=OutcomeService(core),
        recommendations=recommendation_service(core),
    )


__all__ = [
    "CalibrationService",
    "ChildService",
    "EpisodeService",
    "OutcomeService",
    "ServiceRegistry",
    "Services",
    "SubmissionService",
    "build_registry",
]
