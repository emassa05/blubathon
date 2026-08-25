"""Puerto del plan de formulario y del escenario (SPEC 6.9-6.11, 9.7; P1.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PlannedQuestion:
    """Una pregunta del plan. `highlighted=False` significa cola."""

    field_code: str
    highlighted: bool
    reason: str
    voi_nats: float | None = None


@dataclass(frozen=True, slots=True)
class FormPlan:
    """SPEC 6.9. `highlighted + tail` conserva todos los campos aplicables."""

    questions: tuple[PlannedQuestion, ...]
    voi_status: str
    coverage: float | None
    base_slots: int
    outcome_pending: bool
    plan_source: str

    @property
    def highlighted(self) -> tuple[PlannedQuestion, ...]:
        return tuple(question for question in self.questions if question.highlighted)

    @property
    def tail(self) -> tuple[PlannedQuestion, ...]:
        return tuple(question for question in self.questions if not question.highlighted)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """SPEC 9.7. P2 persiste el resultado o la abstención; no replica reglas."""

    available: bool
    schema_version: str
    builder_version: str
    field_values: dict[str, str] = field(default_factory=dict)
    context_tags: tuple[str, ...] = ()
    profile_tags: tuple[str, ...] = ()
    contraindication_tags: tuple[str, ...] = ()
    abstention_reason: str | None = None

    def as_payload(self) -> dict[str, Any]:
        """Representación única de `ScenarioV1`, sin conversión implícita."""
        return {
            "schema_version": self.schema_version,
            "field_values": dict(sorted(self.field_values.items())),
            "context_tags": sorted(set(self.context_tags)),
            "profile_tags": sorted(set(self.profile_tags)),
            "contraindication_tags": sorted(set(self.contraindication_tags)),
        }


class FormPort(Protocol):
    def build_form_plan(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        as_of_at: str,
        audit_mode: bool,
        applicable_fields: tuple[str, ...],
        answered_fields: tuple[str, ...],
        already_presented: tuple[str, ...],
        outcome_pending: bool,
    ) -> FormPlan: ...

    def build_scenario(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        form_session_id: str,
        source: str,
        observations: tuple[dict[str, Any], ...],
        profile: dict[str, Any] | None,
        schema_version: str,
    ) -> ScenarioResult: ...
