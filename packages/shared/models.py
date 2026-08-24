"""Pydantic implementation of the frozen Faro API contract."""

from __future__ import annotations

from datetime import date, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ml.spec_constants import (
    BEHAVIOR_TAGS,
    DYSREGULATION_EVENTS_MAX,
    DYSREGULATION_EVENTS_MIN,
    NIGHT_AWAKENINGS_MAX,
    NIGHT_AWAKENINGS_MIN,
    ORDINAL_MAX,
    ORDINAL_MIN,
    PROVENANCE_FIELDS,
    RISK_MAX,
    RISK_MIN,
    SLEEP_HOURS_MAX,
    SLEEP_HOURS_MIN,
    SOURCE_ALLOWED_FIELDS,
    TEXT_MAX_LENGTH,
)

Probability = Annotated[float, Field(ge=RISK_MIN, le=RISK_MAX)]
Ordinal = Annotated[int, Field(ge=ORDINAL_MIN, le=ORDINAL_MAX)]
ShortText = Annotated[str, Field(max_length=TEXT_MAX_LENGTH)]


class FaroModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Source(StrEnum):
    HOME = "home"
    THERAPY = "therapy"
    SCHOOL = "school"


class CaptureMethod(StrEnum):
    FORM = "form"
    SYNTHETIC = "synthetic"


class FieldProvenance(StrEnum):
    OBSERVED = "observed"
    CONFIRMED = "confirmed"
    ASSUMED_STABLE = "assumed_stable"
    UNKNOWN = "unknown"


class BehaviorTag(StrEnum):
    CALM = BEHAVIOR_TAGS[0]
    IRRITABLE = BEHAVIOR_TAGS[1]
    ANXIOUS = BEHAVIOR_TAGS[2]
    WITHDRAWN = BEHAVIOR_TAGS[3]
    STEREOTYPY = BEHAVIOR_TAGS[4]
    AGGRESSION = BEHAVIOR_TAGS[5]
    SELF_INJURY = BEHAVIOR_TAGS[6]
    MELTDOWN = BEHAVIOR_TAGS[7]
    ELOPEMENT = BEHAVIOR_TAGS[8]
    OTHER = BEHAVIOR_TAGS[9]


def _validate_utc(value: AwareDatetime) -> AwareDatetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must use UTC")
    return value


class DailyLog(FaroModel):
    log_id: UUID4
    child_id: UUID4
    date: date
    source: Source
    sleep_hours: Annotated[float, Field(ge=SLEEP_HOURS_MIN, le=SLEEP_HOURS_MAX)] | None = None
    sleep_quality: Ordinal | None = None
    night_awakenings: (
        Annotated[int, Field(ge=NIGHT_AWAKENINGS_MIN, le=NIGHT_AWAKENINGS_MAX)] | None
    ) = None
    wake_state: Ordinal | None = None
    morning_support_need: Ordinal | None = None
    gi_status: Ordinal | None = None
    food_changes: bool | None = None
    routine_changes: bool | None = None
    observed_behavior_tags: list[BehaviorTag] = Field(default_factory=list)
    observed_behavior_note: ShortText | None = None
    alertness: Ordinal | None = None
    dysregulation_events: (
        Annotated[int, Field(ge=DYSREGULATION_EVENTS_MIN, le=DYSREGULATION_EVENTS_MAX)] | None
    ) = None
    activity_participation: Ordinal | None = None
    social_interactions: Ordinal | None = None
    eating_status: Ordinal | None = None
    relevant_event_flag: bool | None = None
    relevant_events_note: ShortText | None = None
    crisis_occurred: bool
    other_notes: ShortText | None = None
    capture_method: CaptureMethod
    field_provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    created_at: AwareDatetime

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: AwareDatetime) -> AwareDatetime:
        return _validate_utc(value)

    @field_validator("field_provenance")
    @classmethod
    def provenance_keys_are_canonical(
        cls, value: dict[str, FieldProvenance]
    ) -> dict[str, FieldProvenance]:
        unknown_fields = set(value) - set(PROVENANCE_FIELDS)
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"unknown provenance fields: {names}")
        return value

    @model_validator(mode="after")
    def provenance_matches_values(self) -> Self:
        provenance = dict(self.field_provenance)
        for field_name in PROVENANCE_FIELDS:
            value = getattr(self, field_name)
            provenance_value = provenance.get(field_name)
            has_value = value is not None and value != []
            if (
                provenance_value
                in {
                    FieldProvenance.ASSUMED_STABLE.value,
                    FieldProvenance.UNKNOWN.value,
                }
                and has_value
            ):
                raise ValueError(
                    f"provenance_conflict: {field_name} cannot have a value with "
                    f"{provenance_value} provenance"
                )
            if (
                provenance_value
                in {
                    FieldProvenance.OBSERVED.value,
                    FieldProvenance.CONFIRMED.value,
                }
                and not has_value
            ):
                raise ValueError(
                    f"provenance_conflict: {field_name} requires a value with "
                    f"{provenance_value} provenance"
                )
            if has_value and provenance_value is None:
                provenance[field_name] = FieldProvenance.OBSERVED.value
        disallowed_values = {
            field_name
            for field_name in PROVENANCE_FIELDS
            if field_name not in SOURCE_ALLOWED_FIELDS[self.source]
            and getattr(self, field_name) not in (None, [])
        }
        if disallowed_values:
            names = ", ".join(sorted(disallowed_values))
            raise ValueError(f"source {self.source} cannot report fields: {names}")
        self.field_provenance = provenance
        return self


class RequestedVariable(FaroModel):
    variable: str
    prompt_es: str
    voi: float = Field(ge=RISK_MIN)


class RiskResponse(FaroModel):
    child_id: UUID4
    date: date
    status: Literal["ok", "insufficient_data"]
    risk: Probability | None
    risk_band: Literal["verde", "ambar", "rojo"] | None
    interval: tuple[Probability, Probability] | None
    confidence: Literal["alta", "media", "baja"] | None
    icd: Probability
    requested_variables: list[RequestedVariable]
    model_version: str
    generated_at: AwareDatetime

    @field_validator("generated_at")
    @classmethod
    def generated_at_is_utc(cls, value: AwareDatetime) -> AwareDatetime:
        return _validate_utc(value)

    @model_validator(mode="after")
    def status_matches_risk_fields(self) -> Self:
        risk_fields = (self.risk, self.risk_band, self.interval, self.confidence)
        if self.status == "insufficient_data" and any(value is not None for value in risk_fields):
            raise ValueError("insufficient_data responses cannot contain risk values")
        if self.status == "ok" and any(value is None for value in risk_fields):
            raise ValueError("ok responses require risk, band, interval, and confidence")
        if self.interval is not None and self.interval[0] > self.interval[1]:
            raise ValueError("interval lower bound cannot exceed upper bound")
        return self


class VoIItem(RequestedVariable):
    reason: Literal["voi", "staleness", "exploration"]
    suggestion: int | float | bool | None = None
    suggestion_label_es: str | None = None
    days_since_observed: int | None = Field(default=None, ge=0)


class VoIResponse(FaroModel):
    child_id: UUID4
    date: date
    highlighted: list[VoIItem]
    filter_question_es: str
    tail: list[VoIItem]


class Driver(FaroModel):
    variable: str
    shap: float
    direction: Literal["mejora", "empeora"]
    detail_es: str


class Narrative(FaroModel):
    headline_es: str
    explanation_es: str
    actions_es: list[str]


class Strategy(FaroModel):
    id: str
    label_es: str


class ExplainResponse(FaroModel):
    drivers: list[Driver]
    narrative: Narrative
    narrative_source: Literal["llm", "template"]
    strategies: list[Strategy]


class CounterfactualRequest(FaroModel):
    child_id: UUID4
    date: date
    overrides: dict[str, bool | int | float]


class CounterfactualResponse(FaroModel):
    risk_before: Probability
    risk_after: Probability
    band_before: Literal["verde", "ambar", "rojo"]
    band_after: Literal["verde", "ambar", "rojo"]


class QualityResponse(FaroModel):
    icd: Probability
    coverage: Probability
    recency: Probability
    consistency: Probability


class FeedbackRequest(FaroModel):
    child_id: UUID4
    date: date
    dysregulation_occurred: bool
    strategy_used: str | None = None
    helped: bool | None = None


class OkResponse(FaroModel):
    ok: Literal[True]


class IngestResponse(OkResponse):
    child_id: UUID
    date: date


class ErrorDetail(FaroModel):
    code: str
    message_es: str


class ErrorResponse(FaroModel):
    error: ErrorDetail


class EvaluationResponse(FaroModel):
    metrics: dict[str, object]
    baselines: dict[str, object]
    ablations: dict[str, object]
