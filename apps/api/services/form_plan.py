"""Stateless smart-form planning."""

from __future__ import annotations

from apps.api.adapters import Ports
from apps.api.contracts.constants import DEFAULT_WINDOW_DAYS
from apps.api.contracts.field_catalog import DEFAULT_ALLOWLIST_V1, applicable_fields
from apps.api.contracts.models import DefaultSuggestion, FormPlanResponse, FormQuestion


def build(
    *,
    ports: Ports,
    tenant_id: str,
    subject_id: str,
    source: str,
    answers: dict,
    now: str,
) -> FormPlanResponse:
    fields = applicable_fields(source)
    answered = tuple(str(code) for code in answers)
    plan = ports.form.build_form_plan(
        tenant_id=tenant_id,
        subject_id=subject_id,
        source=source,
        as_of_at=now,
        applicable_fields=fields,
        answered_fields=answered,
    )
    questions = []
    for question in plan.questions:
        reason = question.reason
        if reason in {"tail", "voi", "outcome_pending"}:
            reason = "canonical_order"
        questions.append(
            FormQuestion(
                field_code=question.field_code,
                highlighted=question.highlighted,
                reason=reason,
                voi_nats=None,
            )
        )

    defaults = []
    for field_code in DEFAULT_ALLOWLIST_V1:
        if field_code in answers or field_code not in fields:
            continue
        decision = ports.defaults.default_for_field(
            tenant_id=tenant_id,
            subject_id=subject_id,
            source=source,
            field_code=field_code,
            as_of_at=now,
            audit_mode=False,
        )
        if decision is None:
            continue
        defaults.append(
            DefaultSuggestion(
                field_code=field_code,
                value=decision.value,
                window_days=DEFAULT_WINDOW_DAYS,
                sample_size=decision.n_observations,
            )
        )

    return FormPlanResponse(
        questions=questions,
        defaults=defaults,
        voi_status="unavailable_model",
        coverage=0.0 if plan.coverage is None else plan.coverage,
    )
