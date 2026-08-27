"""Puerto del plan de formulario y del escenario (P1.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PlannedQuestion:
    """Una pregunta del plan. `highlighted=False` significa cola."""

    field_code: str
    highlighted: bool
    reason: str
    voi_nats: float | None = None


@dataclass(frozen=True, slots=True)
class FormPlan:
    """`highlighted + tail` conserva todos los campos aplicables."""

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


class FormPort(Protocol):
    def build_form_plan(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        as_of_at: str,
        applicable_fields: tuple[str, ...],
        answered_fields: tuple[str, ...],
    ) -> FormPlan: ...
