"""Daily observations, form sessions and the two kinds of presentation.

The unit of record is a `FieldObservation`, not a mutable row with every field.
A session can produce several of them, each append-only.

Two presentations are recorded for different reasons. `DefaultPresentation` says
a suggestion was shown, which is what makes a later value `default_edited`
instead of manual. `QuestionPresentation` says a field was actually highlighted,
which is what resets the staleness clock; sitting in the tail is not being asked
.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from packages.shared.domain.base import (
    AppendOnlyModel,
    BlubathonModel,
    LocalDate,
    NonNegativeFloat,
    Probability,
    UtcDatetime,
    VersionLabel,
    derive_local_date,
)
from packages.shared.enums import (
    AnswerInteraction,
    DataOrigin,
    EntryMode,
    FieldCode,
    FormSessionKind,
    FormSessionStatus,
    QuestionReason,
    Source,
    VoiStatus,
)
from packages.shared.field_catalog import (
    FIELD_CATALOG,
    FieldValue,
    validate_field_value,
)

VALUE_ASSIGNING_MODES: frozenset[EntryMode] = frozenset(
    {
        EntryMode.MANUAL_NO_DEFAULT,
        EntryMode.AUDIT_MANUAL,
        EntryMode.PROFESSIONAL_OBSERVED,
        EntryMode.IMPORTED_OBSERVED,
        EntryMode.DEFAULT_ACCEPTED,
        EntryMode.DEFAULT_EDITED,
    }
)
# Lo que entrena al estimador de sugerencias. `DEFAULT_ACCEPTED` se queda fuera y
# es INV-02: la sugerencia la propone el propio estimador, asi que aceptarla y
# devolversela le haria aprender de su propia salida. Cada aceptacion volveria la
# siguiente sugerencia mas segura, y el estimador acabaria convencido de un valor
# que nadie llego a reportar nunca. `DEFAULT_EDITED` tampoco entra, por lo mismo
# visto del otro lado: lo que se edita nace de lo que se presento, y el estimador
# no puede medir su propio efecto de presentacion.
DEFAULT_ESTIMATOR_MODES: frozenset[EntryMode] = frozenset(
    {
        EntryMode.MANUAL_NO_DEFAULT,
        EntryMode.AUDIT_MANUAL,
        EntryMode.PROFESSIONAL_OBSERVED,
        EntryMode.IMPORTED_OBSERVED,
    }
)
# Lo que ve el modelo de riesgo. Aqui `DEFAULT_ACCEPTED` **si** entra, y es la
# otra mitad de INV-02, que antes tambien lo excluia.
#
# El bucle que INV-02 evita es el del estimador aprendiendo de si mismo, y ese
# sigue cerrado arriba. El modelo de riesgo no es quien propone la sugerencia:
# para el, un dia aceptado es un dia que alguien miro y dio por bueno, y tirarlo
# no era neutral. Era perder el dia entero, porque a un campo sin observacion el
# challenger no le puede calcular desviacion y se abstiene: un solo campo
# aceptado dejaba la estimacion del dia en la tasa base. Se perdia justo la
# informacion que el formulario se ahorro pedir por conocerla.
#
# Lo que un dia aceptado no es, y por eso no vale igual en todas partes: no es
# una observacion independiente. Su valor lo propuso el estimador desde el
# historial de esa misma persona, asi que confirma la costumbre mas de lo que la
# mide. Quien lea estos datos para medir cuanto ayudan las sugerencias tiene que
# seguir separandolos por `entry_mode`, que para eso se guarda; `ml/form/quality`
# ya lo pesa aparte con `DQI_ACCEPTED_DEFAULT_WEIGHT`.
PRIMARY_REAL_MODEL_MODES: frozenset[EntryMode] = frozenset(
    {
        EntryMode.MANUAL_NO_DEFAULT,
        EntryMode.AUDIT_MANUAL,
        EntryMode.PROFESSIONAL_OBSERVED,
        EntryMode.IMPORTED_OBSERVED,
        EntryMode.DEFAULT_EDITED,
        EntryMode.DEFAULT_ACCEPTED,
    }
)


class SourceMapping(BlubathonModel):
    """A versioned adapter. Unknown source values fail; they never become null."""

    source_mapping_id: UUID
    tenant_id: UUID
    mapping_version: VersionLabel
    field_code: FieldCode
    source: Source
    approved: bool
    content_sha256: str


class FieldObservation(AppendOnlyModel):
    """One observed value, with the provenance that decides how it may be used."""

    field_observation_id: UUID
    subject_id: UUID
    form_session_id: UUID | None = None
    field_code: FieldCode
    value: FieldValue | None = None
    source: Source
    actor_id: UUID
    entry_mode: EntryMode
    data_origin: DataOrigin
    cohort_kind: str
    effective_at: UtcDatetime
    local_date: LocalDate
    source_mapping_id: UUID | None = None
    raw_value: str | None = None

    @property
    def record_id(self) -> UUID:
        return self.field_observation_id

    @property
    def record_kind(self) -> str:
        return "field_observation"

    @property
    def effective_instant(self) -> datetime | None:
        return self.effective_at

    @model_validator(mode="after")
    def _value_matches_field_and_mode(self) -> FieldObservation:
        spec = FIELD_CATALOG[self.field_code]
        if not spec.allows(self.source):
            raise ValueError(f"{self.field_code} is not reportable from {self.source}")

        if self.entry_mode is EntryMode.EXPLICIT_UNKNOWN:
            if self.value is not None:
                raise ValueError("explicit_unknown records no value")
        else:
            if self.value is None:
                raise ValueError(f"{self.entry_mode} must assign a value")
            validate_field_value(self.field_code, self.value)

        if self.entry_mode is EntryMode.IMPORTED_OBSERVED:
            if self.source_mapping_id is None:
                raise ValueError("imported_observed requires an approved source mapping")
        elif self.source_mapping_id is not None:
            raise ValueError("only an import carries a source_mapping_id")

        if self.local_date != derive_local_date(self.effective_at):
            raise ValueError("local_date must be the reference-zone date of effective_at")
        return self

    @property
    def trains_defaults(self) -> bool:
        return self.entry_mode in DEFAULT_ESTIMATOR_MODES and self.data_origin is DataOrigin.REAL

    @property
    def feeds_primary_real_model(self) -> bool:
        return self.entry_mode in PRIMARY_REAL_MODEL_MODES and self.data_origin is DataOrigin.REAL

    def stratum(self) -> tuple[UUID, UUID, Source, FieldCode]:
        """Tenant, subject, source and field. Contexts and tenants never merge."""

        return (self.tenant_id, self.subject_id, self.source, self.field_code)

    def field_day(self) -> tuple[FieldCode, Source, date]:
        return (self.field_code, self.source, self.local_date)


class PosteriorDefault(BlubathonModel):
    """The estimator output behind one suggestion."""

    field_code: FieldCode
    candidate_value: FieldValue
    candidate_count: int = Field(ge=0)
    n_observations: int = Field(ge=0)
    posterior_mean: Probability
    lower_bound: Probability
    quantile: Probability
    estimator_version: VersionLabel

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> PosteriorDefault:
        if self.candidate_count > self.n_observations:
            raise ValueError("candidate_count cannot exceed n_observations")
        validate_field_value(self.field_code, self.candidate_value)
        return self


class DefaultPresentation(BlubathonModel):
    """Proof that a suggestion was shown for this field in this session.

    Its existence is what makes any other value for that field `default_edited`,
    however the client labels it (rule 7).
    """

    default_presentation_id: UUID
    tenant_id: UUID
    form_session_id: UUID
    field_code: FieldCode
    value: FieldValue
    posterior: PosteriorDefault
    presented_at: UtcDatetime

    @model_validator(mode="after")
    def _presented_value_is_the_candidate(self) -> DefaultPresentation:
        if self.posterior.field_code is not self.field_code:
            raise ValueError("posterior belongs to another field")
        if self.value != self.posterior.candidate_value:
            raise ValueError("a presentation shows the posterior candidate, not another value")
        return self


class QuestionPresentation(AppendOnlyModel):
    """Proof that a field was highlighted, which is what "asked" means.

    Appearing in the tail is not being asked and does not reset the clock.
    """

    question_presentation_id: UUID
    subject_id: UUID
    form_session_id: UUID
    field_code: FieldCode
    source: Source
    highlighted: bool
    reason: QuestionReason
    presented_at: UtcDatetime
    local_date: LocalDate
    voi_nats: NonNegativeFloat | None = None
    voi_status: VoiStatus = VoiStatus.UNAVAILABLE_MODEL

    @property
    def record_id(self) -> UUID:
        return self.question_presentation_id

    @property
    def record_kind(self) -> str:
        return "question_presentation"

    @property
    def effective_instant(self) -> datetime | None:
        return self.presented_at

    @model_validator(mode="after")
    def _voi_is_present_only_when_available(self) -> QuestionPresentation:
        if self.voi_status is VoiStatus.AVAILABLE:
            if self.voi_nats is None:
                raise ValueError("an available VoI carries a value in nats")
        elif self.voi_nats is not None:
            raise ValueError("an unavailable VoI is null, never zero")
        return self


class FormSession(BlubathonModel):
    """`opened_at` fixes identity and audit policy; `submitted_at` is the cutoff.

    The browser never decides either one.
    """

    form_session_id: UUID
    tenant_id: UUID
    subject_id: UUID
    actor_id: UUID
    source: Source
    session_kind: FormSessionKind
    status: FormSessionStatus
    audit_mode: bool
    form_policy_version: VersionLabel
    opened_at: UtcDatetime
    submitted_at: UtcDatetime | None = None
    linked_prediction_episode_id: UUID | None = None
    prediction_episode_id: UUID | None = None

    @model_validator(mode="after")
    def _submission_is_consistent(self) -> FormSession:
        if self.status is FormSessionStatus.SUBMITTED:
            if self.submitted_at is None:
                raise ValueError("a submitted session has submitted_at")
            if self.submitted_at < self.opened_at:
                raise ValueError("submitted_at cannot precede opened_at")
        elif self.submitted_at is not None:
            raise ValueError("only a submitted session has submitted_at")

        if self.prediction_episode_id is not None and self.linked_prediction_episode_id is not None:
            raise ValueError("a session either creates an episode or links to one, never both")
        if self.session_kind is FormSessionKind.PROFESSIONAL_OBSERVATION and self.audit_mode:
            raise ValueError("a professional observation session shows no defaults to audit")
        return self


class AnswerSubmission(BlubathonModel):
    """What a client may declare. The server derives `entry_mode` from it."""

    field_code: FieldCode
    interaction: AnswerInteraction
    value: FieldValue | None = None
    default_presentation_id: UUID | None = None

    @model_validator(mode="after")
    def _interaction_carries_what_it_needs(self) -> AnswerSubmission:
        if self.interaction is AnswerInteraction.UNKNOWN:
            if self.value is not None:
                raise ValueError("an explicit unknown carries no value")
            return self
        if self.value is None:
            raise ValueError(f"{self.interaction} must carry a value")
        validate_field_value(self.field_code, self.value)
        responds_to_default = {
            AnswerInteraction.ACCEPT_DEFAULT,
            AnswerInteraction.EDIT_DEFAULT,
        }
        if self.interaction in responds_to_default and self.default_presentation_id is None:
            raise ValueError(f"{self.interaction} requires the presentation it responds to")
        return self


class DataQuality(BlubathonModel):
    """DQI describes quality; it is never a predictive feature or a gate."""

    coverage: Probability
    recency: Probability
    consistency: Probability
    dqi: Probability
    window_days: int = Field(gt=0)
    required_fields: tuple[FieldCode, ...]
    days_since_last_observation: int | None = None
    overlapping_field_days: int = Field(ge=0, default=0)
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dqi_is_the_product(self) -> DataQuality:
        expected = self.coverage * self.recency * self.consistency
        if abs(expected - self.dqi) > 1e-12:
            raise ValueError("dqi must be coverage * recency * consistency")
        return self
