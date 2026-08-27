"""Re-export de los vocabularios cerrados del contrato v0.3.

Los enums viven en `packages/shared/enums.py`, que H1 publicó. `apps/**` no
declara ninguno.

Seis nombres de P2 no coinciden con los de P1 y `apps/**` pasó a usar el nombre
publicado, que es el que manda:

| P2 antes                 | P1 publica                |
|--------------------------|---------------------------|
| `SessionKind`            | `FormSessionKind`         |
| `EpisodeStatus`          | `PredictionEpisodeStatus` |
| `OutcomeValue`           | `OutcomeReportValue`      |
| `ResolutionStatus`       | `OutcomeResolutionStatus` |
| `OutcomeRequestStatus`   | `OutcomeRequestState`     |
| `ItemType`               | `RecommendationItemType`  |
| `CatalogAvailability`    | `CatalogReadiness`        |
| `ReportEstimability`     | `MetricStatus`            |

`PredictionStatus` colisiona: en P2 nombraba el resultado del cierre de sesión y
en P1 nombra el estado de una salida de predicción. P1 manda: el cierre usa
`SubmitStatus` y la salida usa `PredictionStatus`.

`VersionStatus` de P2 mezclaba estrategias, sets y catálogos en un solo enum. P1
los separa en `StrategyStatus` y `CatalogStatus`, que no tienen los mismos
valores.
"""

from __future__ import annotations

from packages.shared.enums import (
    AccreditationCapability,
    Alertness,
    AnswerInteraction,
    ApprovalStatus,
    AttendanceStatus,
    AuthorizationStatus,
    CatalogReadiness,
    CatalogStatus,
    CohortKind,
    ConsentPurpose,
    DailyRegulationState,
    DataOrigin,
    DeploymentMode,
    DocumentStatus,
    EntryMode,
    EpisodeRole,
    ErrorCode,
    EstimateKind,
    EvaluationReportStatus,
    ExecutionStatus,
    FieldCode,
    FieldKind,
    FormSessionKind,
    FormSessionStatus,
    GiStatus,
    GrantCapability,
    IntakeChannel,
    IntendedUse,
    IntervalMethod,
    MedicationAdherence,
    MetricStatus,
    ModelState,
    NonActionableReason,
    OutcomeReportValue,
    OutcomeRequestState,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    PredictionEpisodeStatus,
    PredictionStatus,
    QuestionReason,
    RecommendationAbstentionReason,
    RecommendationItemType,
    RecommendationResponseStatus,
    ReviewDecision,
    ReviewStatus,
    Role,
    RuntimeStatus,
    SleepQuality,
    Source,
    StrategyStatus,
    SubmitStatus,
    TargetScope,
    TimingStatus,
    TrackId,
    VoiStatus,
    WakeState,
)

__all__ = [
    "AccreditationCapability",
    "Alertness",
    "AnswerInteraction",
    "ApprovalStatus",
    "AttendanceStatus",
    "AuthorizationStatus",
    "CatalogReadiness",
    "CatalogStatus",
    "CohortKind",
    "ConsentPurpose",
    "DailyRegulationState",
    "DataOrigin",
    "DeploymentMode",
    "DocumentStatus",
    "EntryMode",
    "EpisodeRole",
    "ErrorCode",
    "EstimateKind",
    "EvaluationReportStatus",
    "ExecutionStatus",
    "FieldCode",
    "FieldKind",
    "FormSessionKind",
    "FormSessionStatus",
    "GiStatus",
    "GrantCapability",
    "IntakeChannel",
    "IntendedUse",
    "IntervalMethod",
    "MedicationAdherence",
    "MetricStatus",
    "ModelState",
    "NonActionableReason",
    "OutcomeReportValue",
    "OutcomeRequestState",
    "OutcomeResolutionStatus",
    "PredictionAbstentionReason",
    "PredictionEpisodeStatus",
    "PredictionStatus",
    "QuestionReason",
    "RecommendationAbstentionReason",
    "RecommendationItemType",
    "RecommendationResponseStatus",
    "ReviewDecision",
    "ReviewStatus",
    "Role",
    "RuntimeStatus",
    "SleepQuality",
    "Source",
    "StrategyStatus",
    "SubmitStatus",
    "TargetScope",
    "TimingStatus",
    "TrackId",
    "VoiStatus",
    "WakeState",
]
