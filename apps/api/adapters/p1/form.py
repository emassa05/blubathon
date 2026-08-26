"""`ml.form` detrás del puerto del formulario stateless.

`build_form_plan` de P1 recibe presentaciones, cobertura y VoI y devuelve un
`FormPlan` con `highlighted` y `tail`; el puerto los guarda en una sola tupla.

El VoI se entrega vacío a propósito: `ml.form.voi` exige un modelo condicional
entrenado y en v0.3 no hay ninguno, así que el plan sale con
`voi_status=unavailable_model` y `voi_nats=null`, nunca cero (INV-09).
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import parse_timestamp
from apps.api.ports.form import FormPlan, PlannedQuestion
from apps.api.store import history
from apps.api.store.db import Database
from ml.form import build_form_plan, compute_dqi
from packages.shared.canonical import local_date
from packages.shared.constants import (
    DQI_WINDOW_DAYS,
    FORM_POLICY_VERSION,
)
from packages.shared.enums import FieldCode, Source

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
        applicable_fields: tuple[str, ...],
        answered_fields: tuple[str, ...],
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
            outcome_pending=False,
            presentations=presentations,
            answered_fields=frozenset(FieldCode(code) for code in answered_fields),
            exploration_secret=self._secret,
            tenant_id=UUID(tenant_id),
            subject_id=UUID(subject_id),
            policy_version=FORM_POLICY_VERSION,
        )

        questions: list[PlannedQuestion] = []
        for question in plan.highlighted:
            questions.append(
                PlannedQuestion(
                    field_code=str(question.field_code),
                    highlighted=True,
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
