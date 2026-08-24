"""Pydantic implementation of the frozen Faro API contract."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from ml.spec_constants import (
    ABSTAIN_ICD,
    ABSTAIN_WIDTH,
    BAND_AMBER,
    BAND_RED,
    BEHAVIOR_TAGS,
    CONFIDENCE_HIGH_ICD,
    CONFIDENCE_HIGH_WIDTH,
    CONFIDENCE_MEDIUM_ICD,
    CONFIDENCE_MEDIUM_WIDTH,
    DYSREGULATION_EVENTS_MAX,
    DYSREGULATION_EVENTS_MIN,
    MEDICATION_ADHERENCE_VALUES,
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
    VOI_MAX_REQUESTED_VARIABLES,
)
from packages.shared.texts import FILTER_QUESTION_ES

Probability = Annotated[StrictFloat, Field(ge=RISK_MIN, le=RISK_MAX)]
Ordinal = Annotated[StrictInt, Field(ge=ORDINAL_MIN, le=ORDINAL_MAX)]
ShortText = Annotated[str, Field(max_length=TEXT_MAX_LENGTH)]


def _parse_canonical_date(value: object) -> date:
    if isinstance(value, datetime):
        raise ValueError("date must not contain a time")
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("date must use YYYY-MM-DD")
    return date.fromisoformat(value)


def _parse_utc_timestamp(value: object) -> object:
    if isinstance(value, str) and ("T" not in value or not value.endswith("Z")):
        raise ValueError("timestamp must use ISO-8601 UTC with a Z suffix")
    return value


CanonicalDate = Annotated[date, BeforeValidator(_parse_canonical_date)]
UtcTimestamp = Annotated[AwareDatetime, BeforeValidator(_parse_utc_timestamp)]


class FaroModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Source(StrEnum):
    HOME = "home"
    THERAPY = "therapy"
    SCHOOL = "school"


class CaptureMethod(StrEnum):
    FORM = "form"
    SYNTHETIC = "synthetic"


class MedicationAdherence(StrEnum):
    TAKEN = MEDICATION_ADHERENCE_VALUES[0]
    MISSED = MEDICATION_ADHERENCE_VALUES[1]
    NOT_APPLICABLE = MEDICATION_ADHERENCE_VALUES[2]


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
    date: CanonicalDate
    source: Source
    sleep_hours: Annotated[StrictFloat, Field(ge=SLEEP_HOURS_MIN, le=SLEEP_HOURS_MAX)] | None = None
    sleep_quality: Ordinal | None = None
    night_awakenings: (
        Annotated[StrictInt, Field(ge=NIGHT_AWAKENINGS_MIN, le=NIGHT_AWAKENINGS_MAX)] | None
    ) = None
    wake_state: Ordinal | None = None
    morning_support_need: Ordinal | None = None
    gi_status: Ordinal | None = None
    medication_adherence: MedicationAdherence | None = None
    food_changes: StrictBool | None = None
    routine_changes: StrictBool | None = None
    observed_behavior_tags: list[BehaviorTag] = Field(default_factory=list)
    observed_behavior_note: ShortText | None = None
    alertness: Ordinal | None = None
    dysregulation_events: (
        Annotated[StrictInt, Field(ge=DYSREGULATION_EVENTS_MIN, le=DYSREGULATION_EVENTS_MAX)] | None
    ) = None
    activity_participation: Ordinal | None = None
    social_interactions: Ordinal | None = None
    eating_status: Ordinal | None = None
    relevant_event_flag: StrictBool | None = None
    relevant_events_note: ShortText | None = None
    crisis_occurred: StrictBool | None = None
    other_notes: ShortText | None = None
    capture_method: CaptureMethod
    field_provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    created_at: UtcTimestamp

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
            has_value = value is not None and (
                value != []
                or (
                    field_name in self.model_fields_set
                    and provenance_value
                    not in {
                        FieldProvenance.ASSUMED_STABLE.value,
                        FieldProvenance.UNKNOWN.value,
                    }
                )
            )
            if (
                provenance_value
                in {
                    FieldProvenance.ASSUMED_STABLE.value,
                    FieldProvenance.UNKNOWN.value,
                }
                and has_value
            ):
                raise PydanticCustomError(
                    "provenance_conflict",
                    "{field_name} cannot have a value with {provenance_value} provenance",
                    {"field_name": field_name, "provenance_value": provenance_value},
                )
            if (
                provenance_value
                in {
                    FieldProvenance.OBSERVED.value,
                    FieldProvenance.CONFIRMED.value,
                }
                and not has_value
            ):
                raise PydanticCustomError(
                    "provenance_conflict",
                    "{field_name} requires a value with {provenance_value} provenance",
                    {"field_name": field_name, "provenance_value": provenance_value},
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
    voi: StrictFloat = Field(ge=RISK_MIN)


class RiskResponse(FaroModel):
    child_id: UUID4
    date: CanonicalDate
    status: Literal["ok", "insufficient_data"]
    risk: Probability | None
    risk_band: Literal["verde", "ambar", "rojo"] | None
    interval: tuple[Probability, Probability] | None
    confidence: Literal["alta", "media", "baja"] | None
    icd: Probability
    requested_variables: list[RequestedVariable] = Field(max_length=VOI_MAX_REQUESTED_VARIABLES)
    model_version: str
    generated_at: UtcTimestamp

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
        if self.status == "insufficient_data" and not self.requested_variables:
            raise ValueError("insufficient_data responses require requested_variables")
        if self.status == "ok":
            if self.icd < ABSTAIN_ICD:
                raise ValueError("ok responses cannot be below the ICD abstention floor")
            width = self.interval[1] - self.interval[0]
            if width > ABSTAIN_WIDTH:
                raise ValueError("ok responses cannot exceed the interval abstention width")
            expected_band = (
                "verde" if self.risk < BAND_AMBER else "ambar" if self.risk < BAND_RED else "rojo"
            )
            if self.risk_band != expected_band:
                raise ValueError("risk_band does not match risk")
            expected_confidence = (
                "alta"
                if self.icd >= CONFIDENCE_HIGH_ICD and width <= CONFIDENCE_HIGH_WIDTH
                else "media"
                if self.icd >= CONFIDENCE_MEDIUM_ICD and width <= CONFIDENCE_MEDIUM_WIDTH
                else "baja"
            )
            if self.confidence != expected_confidence:
                raise ValueError("confidence does not match ICD and interval width")
        return self


class VoIItem(RequestedVariable):
    reason: Literal["voi", "staleness", "exploration"]
    suggestion: StrictInt | StrictFloat | StrictBool | None = None
    suggestion_label_es: str | None = None
    days_since_observed: int | None = Field(default=None, ge=0)


class VoIResponse(FaroModel):
    child_id: UUID4
    date: CanonicalDate
    # SPEC 7.4 asks for two, or three when ICD is low. A day with fewer
    # unanswered variables than that simply has less to highlight; the block
    # never grows past three (SPEC 7.5a).
    highlighted: list[VoIItem] = Field(max_length=3)
    filter_question_es: str
    tail: list[VoIItem]
    closing_question_es: str | None = None
    closing_target_date: CanonicalDate | None = None

    @field_validator("filter_question_es")
    @classmethod
    def filter_question_is_frozen(cls, value: str) -> str:
        if value != FILTER_QUESTION_ES:
            raise ValueError("filter_question_es does not match the frozen text")
        return value


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
    date: CanonicalDate
    overrides: dict[str, StrictBool | StrictInt | StrictFloat]


class CounterfactualResponse(FaroModel):
    risk_before: Probability
    risk_after: Probability
    band_before: Literal["verde", "ambar", "rojo"]
    band_after: Literal["verde", "ambar", "rojo"]

    @model_validator(mode="after")
    def bands_match_probabilities(self) -> Self:
        for probability, band in (
            (self.risk_before, self.band_before),
            (self.risk_after, self.band_after),
        ):
            expected = (
                "verde"
                if probability < BAND_AMBER
                else "ambar"
                if probability < BAND_RED
                else "rojo"
            )
            if band != expected:
                raise ValueError("counterfactual band does not match risk")
        return self


class QualityResponse(FaroModel):
    icd: Probability
    coverage: Probability
    recency: Probability
    consistency: Probability


class FeedbackRequest(FaroModel):
    child_id: UUID4
    date: CanonicalDate
    dysregulation_occurred: StrictBool
    strategy_used: str | None = None
    helped: StrictBool | None = None


class OkResponse(FaroModel):
    ok: Literal[True]


class IngestResponse(OkResponse):
    child_id: UUID4
    date: CanonicalDate


class ErrorDetail(FaroModel):
    code: str
    message_es: str


class ErrorResponse(FaroModel):
    error: ErrorDetail


class EvaluationResponse(FaroModel):
    metrics: dict[str, object]
    baselines: dict[str, object]
    ablations: dict[str, object]
