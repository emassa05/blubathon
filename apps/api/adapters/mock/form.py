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

from typing import Any

from apps.api.contracts.constants import FORM_HIGHLIGHTED_DEFAULT, SCENARIO_SCHEMA_VERSION
from apps.api.contracts.enums import QuestionReason, VoiStatus
from apps.api.contracts.field_catalog import (
    CANONICAL_FIELD_ORDER,
    MONITORED_FIELD_PRIORITY,
    SCENARIO_ALLOWLIST_V1,
)
from apps.api.ports.form import FormPlan, PlannedQuestion, ScenarioResult

PLAN_SOURCE = "mock"
SCENARIO_BUILDER_VERSION = "scenario-builder-mock-0.3.0"


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
        audit_mode: bool,
        applicable_fields: tuple[str, ...],
        answered_fields: tuple[str, ...],
        already_presented: tuple[str, ...],
        outcome_pending: bool,
    ) -> FormPlan:
        answered = set(answered_fields)
        presented = set(already_presented)
        pending = [code for code in applicable_fields if code not in answered]

        # Sin VoI ni antigüedad calculadas, el stub usa la prioridad declarada de
        # SPEC 6.10 y luego el orden canónico. Es determinista y no inventa señal.
        def rank(field_code: str) -> tuple[int, int, str]:
            return (
                MONITORED_FIELD_PRIORITY.get(field_code, len(MONITORED_FIELD_PRIORITY) + 1),
                _canonical_index(field_code),
                field_code,
            )

        candidates = [code for code in sorted(pending, key=rank) if code not in presented]
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
            outcome_pending=outcome_pending,
            plan_source=PLAN_SOURCE,
        )

    def build_scenario(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        form_session_id: str,
        source: str,
        observations: tuple[dict[str, Any], ...],
        profile: dict[str, Any] | None,
        schema_version: str = SCENARIO_SCHEMA_VERSION,
    ) -> ScenarioResult:
        if profile is None:
            # SPEC 9.7 paso 1: sin `profile_version` capturado no hay escenario.
            return ScenarioResult(
                available=False,
                schema_version=schema_version,
                builder_version=SCENARIO_BUILDER_VERSION,
                abstention_reason="scenario_unavailable_profile",
            )

        by_field: dict[str, list[Any]] = {}
        for observation in observations:
            code = observation["field_code"]
            if code not in SCENARIO_ALLOWLIST_V1:
                continue
            if observation.get("value") is None:
                continue  # missing/unknown se omite (SPEC 9.7 paso 2).
            by_field.setdefault(code, []).append(observation["value"])

        field_values: dict[str, str] = {}
        for code, values in by_field.items():
            distinct = {str(value) for value in values}
            if len(distinct) > 1:
                # SPEC 9.7 paso 2: más de una hoja activa es conflicto, no promedio.
                return ScenarioResult(
                    available=False,
                    schema_version=schema_version,
                    builder_version=SCENARIO_BUILDER_VERSION,
                    abstention_reason="scenario_unavailable_conflict",
                )
            field_values[code] = distinct.pop()

        return ScenarioResult(
            available=True,
            schema_version=schema_version,
            builder_version=SCENARIO_BUILDER_VERSION,
            field_values=field_values,
            context_tags=(source,),
            profile_tags=tuple(f"sensory:{tag}" for tag in profile.get("sensory_profile_tags", ()))
            + tuple(
                f"communication:{tag}" for tag in profile.get("communication_support_tags", ())
            ),
            contraindication_tags=tuple(profile.get("contraindication_tags", ())),
        )
