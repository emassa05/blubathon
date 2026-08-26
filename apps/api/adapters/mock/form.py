"""Plan de formulario y escenario fixture (sustituye `ml/form` hasta H1).

Lo que este stub **no** hace, porque es dominio de P1 (TAREAS P1.4):

- No calcula DQI, así que `coverage=None` y `base_slots` usa el valor por defecto.
- No calcula VoI: el estado es `unavailable_model` y `voi_nats` es `None`,
  nunca cero (SPEC 7.3 / INV-09).
- No detecta anomalías ni abre la cola por probabilidad predictiva.

Lo que sí garantiza, porque es contrato y no estadística:

- `highlighted + tail` conserva todos los campos aplicables (INV-10).
- El outcome pendiente es un bloque aparte y no consume cupos.
- Una pregunta ya respondida o ya presentada no se vuelve a destacar.
"""

from __future__ import annotations

from apps.api.contracts.constants import FORM_HIGHLIGHTED_DEFAULT
from apps.api.contracts.enums import QuestionReason, VoiStatus
from apps.api.contracts.field_catalog import (
    CANONICAL_FIELD_ORDER,
    MONITORED_FIELD_PRIORITY,
)
from apps.api.ports.form import FormPlan, PlannedQuestion

PLAN_SOURCE = "mock"


def _canonical_index(field_code: str) -> int:
    return CANONICAL_FIELD_ORDER.index(field_code)


class MockForm:
    def build_form_plan(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        as_of_at: str,
        applicable_fields: tuple[str, ...],
        answered_fields: tuple[str, ...],
    ) -> FormPlan:
        answered = set(answered_fields)
        pending = [code for code in applicable_fields if code not in answered]

        # Sin VoI ni antigüedad calculadas, el stub usa la prioridad declarada de
        # SPEC 6.10 y luego el orden canónico. Es determinista y no inventa señal.
        def rank(field_code: str) -> tuple[int, int, str]:
            return (
                MONITORED_FIELD_PRIORITY.get(field_code, len(MONITORED_FIELD_PRIORITY) + 1),
                _canonical_index(field_code),
                field_code,
            )

        candidates = sorted(pending, key=rank)
        highlighted = candidates[:FORM_HIGHLIGHTED_DEFAULT]
        highlighted_set = set(highlighted)

        questions: list[PlannedQuestion] = [
            PlannedQuestion(
                field_code=code,
                highlighted=True,
                reason=(
                    QuestionReason.STALENESS.value
                    if code in MONITORED_FIELD_PRIORITY
                    else QuestionReason.CANONICAL_ORDER.value
                ),
                voi_nats=None,
            )
            for code in highlighted
        ]
        questions.extend(
            PlannedQuestion(
                field_code=code,
                highlighted=False,
                reason=QuestionReason.TAIL.value,
                voi_nats=None,
            )
            for code in applicable_fields
            if code not in highlighted_set
        )
        return FormPlan(
            questions=tuple(questions),
            voi_status=VoiStatus.UNAVAILABLE_MODEL.value,
            coverage=None,
            base_slots=FORM_HIGHLIGHTED_DEFAULT,
            outcome_pending=False,
            plan_source=PLAN_SOURCE,
        )
