"""EL CONTRATO. Tipos pydantic (PY) — SPEC §2 y §11. Dueño: P1.

Espejo TS (zod) pendiente para apps/web (Fase 2).
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from ml.errors import ContractViolationError
from ml.spec_constants import (
    BEHAVIOR_TAG_ENUM,
    CAPTURE_METHOD_ENUM,
    PROVENANCE_ENUM,
    SOURCE_ENUM,
)

BehaviorTag = Literal[
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
]
Source = Literal["home", "therapy", "school"]
CaptureMethod = Literal["form", "synthetic", "voice"]
Provenance = Literal["observed", "confirmed", "assumed_stable", "unknown"]
RiskBand = Literal["verde", "ambar", "rojo"]
Confidence = Literal["alta", "media", "baja"]
NarrativeSource = Literal["llm", "template"]
VoiReason = Literal["voi", "staleness", "exploration"]
Status = Literal["ok", "insufficient_data"]

assert set(BehaviorTag.__args__) == set(BEHAVIOR_TAG_ENUM)
assert set(Source.__args__) == set(SOURCE_ENUM)
assert set(CaptureMethod.__args__) == set(CAPTURE_METHOD_ENUM)
assert set(Provenance.__args__) == set(PROVENANCE_ENUM)


class DailyLog(BaseModel):
    """SPEC §2.4 — el objeto JSON canónico."""

    log_id: str = Field(default_factory=lambda: str(uuid4()))
    child_id: str
    date: str
    source: Source
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    night_awakenings: int | None = None
    wake_state: int | None = None
    morning_support_need: int | None = None
    gi_status: int | None = None
    food_changes: bool | None = None
    routine_changes: bool | None = None
    observed_behavior_tags: list[BehaviorTag] = Field(default_factory=list)
    observed_behavior_note: str | None = Field(default=None, max_length=500)
    alertness: int | None = None
    dysregulation_events: int | None = None
    activity_participation: int | None = None
    social_interactions: int | None = None
    eating_status: int | None = None
    relevant_event_flag: bool | None = None
    relevant_events_note: str | None = Field(default=None, max_length=500)
    crisis_occurred: bool | None = None
    other_notes: str | None = Field(default=None, max_length=500)
    capture_method: CaptureMethod = "form"
    field_provenance: dict[str, Provenance] = Field(default_factory=dict)
    created_at: str | None = None

    @model_validator(mode="after")
    def _check_assumed_stable_sin_valor(self) -> "DailyLog":
        """SPEC §2.5 — assumed_stable nunca asigna valor."""
        for field, prov in self.field_provenance.items():
            if prov == "assumed_stable" and getattr(self, field, None) is not None:
                raise ContractViolationError(
                    f"provenance_conflict: '{field}' es assumed_stable pero tiene valor"
                )
        return self


class RequestedVariable(BaseModel):
    variable: str
    prompt_es: str
    voi: float


class RiskResponse(BaseModel):
    """SPEC §11.1 — contrato central."""

    child_id: str
    date: str
    status: Status
    risk: float | None = None
    risk_band: RiskBand | None = None
    interval: tuple[float, float] | None = None
    confidence: Confidence | None = None
    icd: float | None = None
    requested_variables: list[RequestedVariable] = Field(default_factory=list)
    model_version: str
    generated_at: str


class VoiItem(BaseModel):
    variable: str
    prompt_es: str
    voi: float
    reason: VoiReason
    suggestion: float | int | None = None
    suggestion_label_es: str | None = None
    days_since_observed: int | None = None


class VoIResponse(BaseModel):
    """SPEC §11.2."""

    child_id: str
    date: str
    highlighted: list[VoiItem]
    filter_question_es: str
    tail: list[VoiItem]
    closing_question_es: str | None = None
    closing_target_date: str | None = None


class Driver(BaseModel):
    variable: str
    shap: float
    direction: str
    detail_es: str


class Narrative(BaseModel):
    headline_es: str
    explanation_es: str
    actions_es: list[str]


class Strategy(BaseModel):
    id: str
    label_es: str


class ExplainResponse(BaseModel):
    """SPEC §11.3."""

    drivers: list[Driver]
    narrative: Narrative
    narrative_source: NarrativeSource
    strategies: list[Strategy]
