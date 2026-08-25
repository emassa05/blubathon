"""Construcción y persistencia del plan de formulario (SPEC 6.6-6.9, 11.3).

El plan lo calcula P1 a través del puerto; P2 persiste qué se destacó y qué
sugerencia se mostró, que es lo que permite reproducir antigüedad y auditoría.
"""

from __future__ import annotations

import sqlite3

from apps.api.adapters import Ports
from apps.api.contracts.enums import FormSessionKind, QuestionReason, Source, VoiStatus
from apps.api.contracts.field_catalog import (
    DEFAULT_ALLOWLIST_V1,
    FIELD_CATALOG,
    applicable_fields,
)
from apps.api.contracts.models import (
    DefaultSuggestion,
    FormQuestion,
    OutcomePendingBlock,
)
from apps.api.ports import FormPlan, PlannedQuestion
from apps.api.store import form_sessions as sessions_store
from apps.api.store.json_columns import load, load_list


def stored_plan(connection: sqlite3.Connection, *, session: sqlite3.Row) -> FormPlan:
    """Plan ya persistido de una sesión cerrada.

    Una sesión enviada no vuelve a presentar preguntas: recalcular reiniciaría el
    reloj de antigüedad de SPEC 6.10 con presentaciones que nadie vio.
    """
    source = Source(session["source"])
    rows = connection.execute(
        "SELECT field_code, reason, voi_nats FROM question_presentations"
        " WHERE form_session_id = ? ORDER BY position",
        (session["form_session_id"],),
    ).fetchall()
    highlighted = [
        PlannedQuestion(
            field_code=row["field_code"],
            highlighted=True,
            reason=row["reason"],
            voi_nats=row["voi_nats"],
        )
        for row in rows
    ]
    seen = {question.field_code for question in highlighted}
    tail = [
        PlannedQuestion(
            field_code=code,
            highlighted=False,
            reason=QuestionReason.TAIL.value,
            voi_nats=None,
        )
        for code in applicable_fields(source)
        if code not in seen
    ]
    has_voi = any(question.voi_nats is not None for question in highlighted)
    return FormPlan(
        questions=tuple(highlighted + tail),
        voi_status=(VoiStatus.AVAILABLE.value if has_voi else VoiStatus.UNAVAILABLE_MODEL.value),
        coverage=None,
        base_slots=len(highlighted),
        outcome_pending=False,
        plan_source="persisted",
    )


def build_and_persist(
    connection: sqlite3.Connection,
    *,
    ports: Ports,
    session: sqlite3.Row,
    now: str,
    outcome_pending: bool,
) -> FormPlan:
    """Recalcula el plan y registra presentaciones nuevas.

    Conserva preguntas ya respondidas y no vuelve a presentar la misma en la
    sesión (SPEC 6.9). `record_question_presentation` es idempotente por
    `(sesión, campo)`.
    """
    source = Source(session["source"])
    fields = applicable_fields(source)
    answered = sessions_store.answered_field_codes(connection, session["form_session_id"])
    presented = sessions_store.presented_field_codes(connection, session["form_session_id"])

    plan = ports.form.build_form_plan(
        tenant_id=session["tenant_id"],
        subject_id=session["subject_id"],
        source=source.value,
        as_of_at=now,
        audit_mode=bool(session["audit_mode"]),
        applicable_fields=fields,
        answered_fields=answered,
        already_presented=presented,
        outcome_pending=outcome_pending,
    )

    for position, question in enumerate(plan.questions):
        sessions_store.record_question_presentation(
            connection,
            tenant_id=session["tenant_id"],
            subject_id=session["subject_id"],
            form_session_id=session["form_session_id"],
            field_code=question.field_code,
            highlighted=question.highlighted,
            reason=question.reason,
            voi_nats=question.voi_nats,
            position=position,
            source=source.value,
            local_date=session["local_date"],
            presented_at=now,
        )

    _persist_defaults(
        connection,
        ports=ports,
        session=session,
        source=source,
        answered=set(answered),
        now=now,
    )
    return plan


def _persist_defaults(
    connection: sqlite3.Connection,
    *,
    ports: Ports,
    session: sqlite3.Row,
    source: Source,
    answered: set[str],
    now: str,
) -> None:
    """SPEC 6.6 y 6.8: una sesión auditada o profesional no muestra sugerencias."""
    if bool(session["audit_mode"]):
        return
    if session["session_kind"] == FormSessionKind.PROFESSIONAL_OBSERVATION.value:
        return
    for field_code in DEFAULT_ALLOWLIST_V1:
        if field_code in answered or source not in _sources_for(field_code):
            continue
        if sessions_store.current_default_presentation(
            connection, form_session_id=session["form_session_id"], field_code=field_code
        ):
            continue
        decision = ports.defaults.default_for_field(
            tenant_id=session["tenant_id"],
            subject_id=session["subject_id"],
            source=source.value,
            field_code=field_code,
            as_of_at=now,
            audit_mode=bool(session["audit_mode"]),
        )
        if decision is None:
            continue
        sessions_store.record_default_presentation(
            connection,
            tenant_id=session["tenant_id"],
            subject_id=session["subject_id"],
            form_session_id=session["form_session_id"],
            field_code=field_code,
            value=decision.value,
            candidate_count=decision.candidate_count,
            posterior_mean=decision.posterior_mean,
            lower_bound=decision.lower_bound,
            n_observations=decision.n_observations,
            estimator_version=decision.estimator_version,
            presented_at=now,
        )


def _sources_for(field_code: str) -> frozenset[Source]:
    return FIELD_CATALOG[field_code].allowed_sources


def question_views(
    connection: sqlite3.Connection, *, plan: FormPlan, form_session_id: str
) -> tuple[list[FormQuestion], list[FormQuestion]]:
    """SPEC 11.3. `highlighted + tail` conserva todos los campos aplicables."""
    defaults = {
        row["field_code"]: row
        for row in sessions_store.session_default_presentations(connection, form_session_id)
    }

    def view(field_code: str, reason: str, voi_nats: float | None) -> FormQuestion:
        row = defaults.get(field_code)
        suggestion = (
            None
            if row is None
            else DefaultSuggestion(
                presentation_id=row["default_presentation_id"],
                value=load(row["candidate_value"]),
                candidate_count=row["candidate_count"],
                posterior_mean=row["posterior_mean"],
                lower_bound=row["lower_bound"],
                n_observations=row["n_observations"],
                estimator_version=row["estimator_version"],
            )
        )
        return FormQuestion(
            field_code=field_code, reason=reason, voi_nats=voi_nats, default=suggestion
        )

    highlighted = [
        view(question.field_code, question.reason, question.voi_nats)
        for question in plan.highlighted
    ]
    tail = [view(question.field_code, question.reason, question.voi_nats) for question in plan.tail]
    return highlighted, tail


def outcome_block(
    connection: sqlite3.Connection,
    *,
    request_row: sqlite3.Row,
    target_row: sqlite3.Row,
    state: str,
) -> OutcomePendingBlock:
    return OutcomePendingBlock(
        prediction_episode_id=request_row["prediction_episode_id"],
        question_es=target_row["question_es"],
        severity_anchors_es=[str(item) for item in load_list(target_row["severity_anchors_es"])],
        target_end_at=request_row["target_end_at"],
        capture_deadline_at=request_row["capture_deadline_at"],
        state=state,
    )
