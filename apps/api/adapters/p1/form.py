"""`ml.form` detrás del puerto del formulario (SPEC 6.9-6.11, 7.1, 9.7).

`build_form_plan` de P1 recibe presentaciones, cobertura y VoI y devuelve un
`FormPlan` con `highlighted` y `tail`; el puerto de P2 los guarda en una sola
tupla de preguntas. `build_scenario` recibe una sesión enviada completa y
devuelve un `ScenarioBuildResult`. Toda la conversión vive aquí.

El VoI se entrega vacío a propósito: `ml.form.voi` exige un modelo condicional
entrenado y en v0.3 no hay ninguno, así que el plan sale con
`voi_status=unavailable_model` y `voi_nats=null`, nunca cero (INV-09).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import parse_timestamp
from apps.api.ports.form import FormPlan, PlannedQuestion, ScenarioResult
from apps.api.store import form_sessions as sessions_store
from apps.api.store import history
from apps.api.store.db import Database
from ml.form import build_form_plan, build_scenario, compute_dqi
from ml.form.scenario import ScenarioInputs
from packages.shared.canonical import local_date
from packages.shared.constants import (
    DQI_WINDOW_DAYS,
    FORM_POLICY_VERSION,
    SCENARIO_BUILDER_VERSION,
    SCENARIO_SCHEMA_VERSION,
)
from packages.shared.enums import FieldCode, RuntimeStatus, Source

PLAN_SOURCE = "p1"


class P1Form:
    def __init__(self, *, database: Database, secret: bytes) -> None:
        self._database = database
        self._secret = secret

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
        cutoff = parse_timestamp(as_of_at)
        connection = self._database.connection
        since = (cutoff.date() - timedelta(days=DQI_WINDOW_DAYS)).isoformat()
        observations = [
            translate.field_observation(row)
            for row in history.observations_for_subject(
                connection, tenant_id=tenant_id, subject_id=subject_id, since_local_date=since
            )
        ]
        presentations = [
            translate.question_presentation(row)
            for row in history.presentations_for_subject(
                connection, tenant_id=tenant_id, subject_id=subject_id
            )
        ]
        quality = compute_dqi(observations, as_of_at=cutoff)

        plan = build_form_plan(
            source=Source(source),
            today=local_date(cutoff),
            cutoff=cutoff,
            coverage=quality.coverage,
            outcome_pending=outcome_pending,
            presentations=presentations,
            answered_fields=frozenset(FieldCode(code) for code in answered_fields),
            exploration_secret=self._secret,
            tenant_id=UUID(tenant_id),
            subject_id=UUID(subject_id),
            policy_version=FORM_POLICY_VERSION,
        )

        # SPEC 6.9: una pregunta ya presentada en esta sesión no se vuelve a
        # destacar. P1 planifica sobre el historial; qué se mostró ya en esta
        # sesión es estado de la sesión, y por eso lo aplica el adaptador.
        presented = set(already_presented)
        questions: list[PlannedQuestion] = []
        for question in plan.highlighted:
            questions.append(
                PlannedQuestion(
                    field_code=str(question.field_code),
                    highlighted=str(question.field_code) not in presented,
                    reason=question.reason.value,
                    voi_nats=None if question.voi is None else question.voi.voi_nats,
                )
            )
        chosen = {question.field_code for question in questions}
        for question in plan.tail:
            if str(question.field_code) in chosen:
                continue
            questions.append(
                PlannedQuestion(
                    field_code=str(question.field_code),
                    highlighted=False,
                    reason=question.reason.value,
                    voi_nats=None if question.voi is None else question.voi.voi_nats,
                )
            )
        # INV-10: `highlighted + tail` conserva todos los campos aplicables.
        for code in applicable_fields:
            if code in {question.field_code for question in questions}:
                continue
            questions.append(
                PlannedQuestion(
                    field_code=code,
                    highlighted=False,
                    reason="tail",
                    voi_nats=None,
                )
            )
        return FormPlan(
            questions=tuple(questions),
            voi_status=plan.voi_status.value,
            coverage=quality.coverage,
            base_slots=plan.base_slots,
            outcome_pending=plan.outcome_pending,
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
        connection = self._database.connection
        session_row = sessions_store.session(connection, form_session_id)
        if session_row is None or session_row["submitted_at"] is None:
            return ScenarioResult(
                available=False,
                schema_version=schema_version,
                builder_version=SCENARIO_BUILDER_VERSION,
                abstention_reason="scenario_unavailable_conflict",
            )
        session = translate.form_session(session_row)
        profile_rows = history.subject_profile_rows(
            connection,
            tenant_id=tenant_id,
            subject_id=subject_id,
            cutoff=session_row["submitted_at"],
        )
        if not profile_rows:
            # SPEC 9.7 paso 1: sin perfil versionado no hay escenario. P1 lo
            # trata como error de programación, así que el adaptador se abstiene
            # antes de llamarlo.
            return ScenarioResult(
                available=False,
                schema_version=schema_version,
                builder_version=SCENARIO_BUILDER_VERSION,
                abstention_reason="scenario_unavailable_profile",
            )
        session_observations = [
            translate.field_observation(row)
            for row in history.observations_for_session(connection, form_session_id=form_session_id)
        ]
        result = build_scenario(
            ScenarioInputs(
                form_session=session,
                as_of_at=session.submitted_at,
                observations=session_observations,
                profile=translate.subject_profile(profile_rows[-1]),
                context_tags=frozenset({Source(source).value}),
                tenant_secret=self._secret,
            ),
            submitted_form_session_id=UUID(form_session_id),
            scenario_schema_version=schema_version,
        )
        if result.status is not RuntimeStatus.MATCHED or result.scenario is None:
            reasons = tuple(reason.value for reason in result.reasons)
            return ScenarioResult(
                available=False,
                schema_version=schema_version,
                builder_version=result.builder_version,
                abstention_reason=reasons[0] if reasons else "scenario_unavailable_conflict",
            )
        scenario = result.scenario
        return ScenarioResult(
            available=True,
            schema_version=scenario.schema_version,
            builder_version=result.builder_version,
            field_values={str(code): value for code, value in scenario.field_values.items()},
            context_tags=tuple(scenario.context_tags),
            profile_tags=tuple(scenario.profile_tags),
            contraindication_tags=tuple(scenario.contraindication_tags),
        )
