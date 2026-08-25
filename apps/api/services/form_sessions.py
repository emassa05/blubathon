"""Servicio de sesiones de formulario (SPEC 4.1-4.2, 5.5, 6, 11.3).

Reglas duras que este servicio garantiza:

- Una sugerencia no tocada no crea observación (INV-01).
- `audit_mode` se fija al abrir y no cambia al recargar (INV-05).
- Submit siempre cierra la sesión. Sin target seleccionable no nace episodio ni
  outcome request (INV-13). Con un target primario abierto, la sesión se enlaza
  y no se crean ventanas solapadas.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from apps.api.auth.context import ActorContext
from apps.api.canonical import canonical_timestamp, keyed_scenario_hash, parse_timestamp
from apps.api.contracts.constants import (
    FORM_POLICY_VERSION,
    OUTCOME_CAPTURE_LIMIT_HOURS,
    SCENARIO_SCHEMA_VERSION,
    TARGET_HORIZON_HOURS,
)
from apps.api.contracts.enums import (
    AnswerInteraction,
    CohortKind,
    ConsentPurpose,
    DataOrigin,
    FormSessionKind,
    FormSessionStatus,
    GrantCapability,
    IntakeChannel,
    OutcomeResolutionStatus,
    Role,
    RuntimeStatus,
    Source,
    SubmitStatus,
)
from apps.api.contracts.field_catalog import (
    UnknownFieldValueError,
    applicable_fields,
    validate_field_value,
)
from apps.api.contracts.models import (
    AnswerAcceptedView,
    AnswerRequest,
    FormSessionCreateRequest,
    FormSessionView,
    SubmitFormSessionView,
)
from apps.api.errors import invalid, not_found
from apps.api.services import form_plan
from apps.api.services.base import Services
from apps.api.services.entry_mode import derive_entry_mode
from apps.api.services.local_time import local_date
from apps.api.store import audit, catalog, episodes, identity, outcomes, recommendations
from apps.api.store import form_sessions as sessions_store
from apps.api.store.json_columns import load, load_list


@dataclass(frozen=True, slots=True)
class SubmitOutcome:
    view: SubmitFormSessionView


class FormSessionService:
    def __init__(self, services: Services) -> None:
        self._services = services

    # -- reautorización de replay -----------------------------------------

    def authorize_open(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        subject_id: str,
        now: str,
    ) -> None:
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=subject_id,
            capability=GrantCapability.SUBJECT_READ,
            cutoff=now,
            action="form_session_open_replay",
        )

    def authorize_session(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        form_session_id: str,
        capability: GrantCapability,
        now: str,
    ) -> None:
        session = self._session(connection, actor=actor, form_session_id=form_session_id)
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=session["subject_id"],
            capability=capability,
            cutoff=now,
            action="form_session_replay",
        )

    # -- abrir -----------------------------------------------------------

    def open(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        request: FormSessionCreateRequest,
        now: str,
    ) -> FormSessionView:
        subject_id = str(request.subject_id)
        authorization = self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=subject_id,
            capability=GrantCapability.SUBJECT_READ,
            cutoff=now,
            action="form_session_open",
        )
        session_kind = FormSessionKind(request.session_kind)
        if session_kind is FormSessionKind.PROFESSIONAL_OBSERVATION and not actor.has_role(
            Role.PROFESSIONAL
        ):
            raise invalid("role_not_allowed")

        day = local_date(parse_timestamp(now))
        assignment = self._services.ports.defaults.assign_audit_mode(
            tenant_id=actor.tenant_id,
            subject_id=subject_id,
            local_date=day,
            policy_version=FORM_POLICY_VERSION,
        )
        form_session_id = sessions_store.open_session(
            connection,
            sessions_store.NewSession(
                tenant_id=actor.tenant_id,
                subject_id=subject_id,
                actor_id=actor.actor_id,
                source=Source(request.source).value,
                session_kind=session_kind.value,
                audit_mode=assignment.audit_mode,
                audit_bucket=assignment.bucket,
                form_policy_version=assignment.policy_version,
                local_date=day.isoformat(),
                opened_at=now,
            ),
        )
        audit.record(
            connection,
            actor=actor,
            action="form_session_open",
            resource_type="form_session",
            resource_id=form_session_id,
            subject_id=subject_id,
            decision="allowed",
            occurred_at=now,
            request_id=actor.request_id,
        )
        _ = authorization
        return self.view(connection, actor=actor, form_session_id=form_session_id, now=now)

    # -- responder -------------------------------------------------------

    def answer(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        form_session_id: str,
        request: AnswerRequest,
        now: str,
    ) -> AnswerAcceptedView:
        session = self._session_for_write(connection, actor=actor, form_session_id=form_session_id)
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=session["subject_id"],
            capability=GrantCapability.DAILY_OBSERVATION_WRITE,
            cutoff=now,
            action="form_answer",
        )
        source = Source(session["source"])
        answer = request.answer
        if answer.field_code not in applicable_fields(source):
            raise invalid("field_not_allowed_for_source", field_code=answer.field_code)

        presentation = sessions_store.current_default_presentation(
            connection, form_session_id=form_session_id, field_code=answer.field_code
        )
        interaction = AnswerInteraction(answer.interaction)
        if answer.default_presentation_id is not None and (
            presentation is None
            or presentation["default_presentation_id"] != str(answer.default_presentation_id)
        ):
            raise invalid("default_presentation_not_current")

        entry_mode = derive_entry_mode(
            intake_channel=IntakeChannel.FORM,
            session_kind=FormSessionKind(session["session_kind"]),
            audit_mode=bool(session["audit_mode"]),
            interaction=interaction,
            has_current_presentation=presentation is not None,
        )

        value: Any | None
        if interaction is AnswerInteraction.UNKNOWN:
            if answer.value is not None:
                raise invalid("validation_error", reason="unknown_carries_no_value")
            value = None
        elif interaction is AnswerInteraction.ACCEPT_DEFAULT:
            # `AnswerSubmission` exige que quien acepta declare el valor que
            # aceptó. El servidor no lo cree: lo compara con lo presentado, y si
            # no coincide la interacción declarada es falsa (SPEC 5.5 regla 7).
            if presentation is None:
                raise invalid("default_presentation_not_current")
            value = load(presentation["candidate_value"])
            if validate_field_value(answer.field_code, answer.value) != value:
                raise invalid("validation_error", reason="accepted_value_is_not_the_presented_one")
        else:
            try:
                value = validate_field_value(answer.field_code, answer.value)
            except UnknownFieldValueError as error:
                raise invalid("validation_error", field_code=error.field_code) from error

        supersedes_id = None if answer.supersedes_id is None else str(answer.supersedes_id)
        if supersedes_id is not None:
            previous = connection.execute(
                "SELECT field_observation_id FROM field_observations"
                " WHERE field_observation_id = ? AND tenant_id = ? AND form_session_id = ?"
                " AND field_code = ?",
                (supersedes_id, actor.tenant_id, form_session_id, answer.field_code),
            ).fetchone()
            if previous is None:
                raise invalid("validation_error", reason="supersedes_id_not_correctable")

        effective_at = (
            now if answer.effective_at is None else canonical_timestamp(answer.effective_at)
        )
        if effective_at > now:
            # El cliente puede declarar un tiempo efectivo, nunca uno futuro.
            raise invalid("validation_error", reason="effective_at_in_the_future")

        subject = identity.subject(connection, session["subject_id"])
        assert subject is not None
        field_observation_id = sessions_store.insert_observation(
            connection,
            sessions_store.NewObservation(
                tenant_id=actor.tenant_id,
                subject_id=session["subject_id"],
                form_session_id=form_session_id,
                field_code=answer.field_code,
                value=value,
                source=source.value,
                actor_id=actor.actor_id,
                entry_mode=entry_mode.value,
                data_origin=_origin_for(subject["cohort_kind"]).value,
                cohort_kind=subject["cohort_kind"],
                effective_at=effective_at,
                ingested_at=now,
                local_date=local_date(parse_timestamp(effective_at)).isoformat(),
                default_presentation_id=(
                    None if presentation is None else presentation["default_presentation_id"]
                ),
                supersedes_id=supersedes_id,
            ),
        )
        audit.record(
            connection,
            actor=actor,
            action="field_observation_write",
            resource_type="field_observation",
            resource_id=field_observation_id,
            subject_id=session["subject_id"],
            decision="allowed",
            reason_code=entry_mode.value,
            occurred_at=now,
            request_id=actor.request_id,
        )
        return AnswerAcceptedView(
            field_observation_id=field_observation_id,
            field_code=answer.field_code,
            entry_mode=entry_mode.value,
            session=self.view(connection, actor=actor, form_session_id=form_session_id, now=now),
        )

    # -- cerrar ----------------------------------------------------------

    def submit(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        form_session_id: str,
        now: str,
    ) -> SubmitFormSessionView:
        session = self._session_for_write(connection, actor=actor, form_session_id=form_session_id)
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=session["subject_id"],
            capability=GrantCapability.FORM_SUBMIT,
            cutoff=now,
            action="form_submit",
        )
        subject = identity.subject(connection, session["subject_id"])
        assert subject is not None
        cohort = CohortKind(subject["cohort_kind"])

        scope = "demo_fixture" if cohort is CohortKind.DEMO_FIXTURE else "tenant"
        target_row, reason = identity.select_target_definition(
            connection,
            scope=scope,
            tenant_id=None if cohort is CohortKind.DEMO_FIXTURE else actor.tenant_id,
            cutoff=now,
        )
        if target_row is None:
            # SPEC 4.2: la sesión cierra y conserva observaciones, pero no fabrica
            # un target ni un outcome request.
            sessions_store.close_session(
                connection,
                form_session_id=form_session_id,
                submitted_at=now,
                prediction_status=reason,
                prediction_episode_id=None,
                linked_prediction_episode_id=None,
            )
            audit.record(
                connection,
                actor=actor,
                action="form_submit",
                resource_type="form_session",
                resource_id=form_session_id,
                subject_id=session["subject_id"],
                decision="allowed",
                reason_code=reason,
                occurred_at=now,
                request_id=actor.request_id,
            )
            return SubmitFormSessionView(
                form_session_id=form_session_id,
                status=SubmitStatus.TARGET_DEFINITION_UNAVAILABLE.value,
                submitted_at=now,
                reasons=[reason],
            )

        open_episode = sessions_store.open_primary_episode(
            connection,
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            at=now,
        )
        if open_episode is not None:
            # SPEC 4.2: un target abierto enlaza la sesión y no crea otro episodio.
            sessions_store.close_session(
                connection,
                form_session_id=form_session_id,
                submitted_at=now,
                prediction_status=SubmitStatus.EPISODE_LINKED.value,
                prediction_episode_id=None,
                linked_prediction_episode_id=open_episode["prediction_episode_id"],
            )
            existing_request = outcomes.outcome_request(
                connection, open_episode["prediction_episode_id"]
            )
            existing_instance = recommendations.instance_for_episode(
                connection, open_episode["prediction_episode_id"]
            )
            return SubmitFormSessionView(
                form_session_id=form_session_id,
                status=SubmitStatus.EPISODE_LINKED.value,
                submitted_at=now,
                linked_prediction_episode_id=open_episode["prediction_episode_id"],
                outcome_request_id=(
                    None if existing_request is None else existing_request["outcome_request_id"]
                ),
                recommendation_instance_id=(
                    None
                    if existing_instance is None
                    else existing_instance["recommendation_instance_id"]
                ),
            )

        view = self._create_episode(
            connection,
            actor=actor,
            session=session,
            subject=subject,
            target_row=target_row,
            now=now,
        )
        audit.record(
            connection,
            actor=actor,
            action="form_submit",
            resource_type="prediction_episode",
            resource_id=str(view.prediction_episode_id),
            subject_id=session["subject_id"],
            decision="allowed",
            reason_code=SubmitStatus.EPISODE_CREATED.value,
            occurred_at=now,
            request_id=actor.request_id,
        )
        return view

    def _create_episode(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        session: sqlite3.Row,
        subject: sqlite3.Row,
        target_row: sqlite3.Row,
        now: str,
    ) -> SubmitFormSessionView:
        """Todo lo del episodio ocurre en la transacción abierta por la ruta."""
        as_of = parse_timestamp(now)
        target_end_at = canonical_timestamp(as_of + timedelta(hours=TARGET_HORIZON_HOURS))
        capture_deadline_at = canonical_timestamp(
            as_of + timedelta(hours=OUTCOME_CAPTURE_LIMIT_HOURS)
        )
        origin = _origin_for(subject["cohort_kind"])
        profile = identity.active_profile(
            connection,
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            cutoff=now,
        )

        sessions_store.close_session(
            connection,
            form_session_id=session["form_session_id"],
            submitted_at=now,
            prediction_status=SubmitStatus.EPISODE_CREATED.value,
            prediction_episode_id=None,
            linked_prediction_episode_id=None,
        )
        prediction_episode_id = episodes.create_primary_episode(
            connection,
            episodes.NewEpisode(
                tenant_id=actor.tenant_id,
                subject_id=session["subject_id"],
                form_session_id=session["form_session_id"],
                as_of_at=now,
                target_start_at=now,
                target_end_at=target_end_at,
                capture_deadline_at=capture_deadline_at,
                target_definition_version=target_row["target_definition_version"],
                profile_version=None if profile is None else profile["profile_version"],
                care_mode=None if profile is None else profile["care_mode"],
                input_data_origin=origin.value,
                created_at=now,
            ),
        )
        connection.execute(
            "UPDATE form_sessions SET prediction_episode_id = ? WHERE form_session_id = ?",
            (prediction_episode_id, session["form_session_id"]),
        )

        projected = sessions_store.projected_session_observations(
            connection, form_session_id=session["form_session_id"], cutoff=now
        )
        consent_ids = self._services.authorization.active_consents(
            connection,
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            purpose=ConsentPurpose.OPERATIONAL_SUPPORT,
            cutoff=now,
        )
        episodes.create_feature_snapshot(
            connection,
            tenant_id=actor.tenant_id,
            prediction_episode_id=prediction_episode_id,
            as_of_at=now,
            input_data_origin=origin.value,
            projected_observation_ids=tuple(row["field_observation_id"] for row in projected),
            projected_outcome_ids=(),
            consent_ids=consent_ids,
            profile_version=None if profile is None else profile["profile_version"],
            care_mode=None if profile is None else profile["care_mode"],
            created_at=now,
        )

        for output in self._services.ports.prediction.predict(
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            prediction_episode_id=prediction_episode_id,
            as_of_at=now,
            cohort_kind=subject["cohort_kind"],
            input_data_origin=origin.value,
            care_mode=None if profile is None else profile["care_mode"],
            target_definition_version=target_row["target_definition_version"],
            snapshot={"observation_ids": [row["field_observation_id"] for row in projected]},
        ):
            episodes.insert_prediction_output(
                connection,
                tenant_id=actor.tenant_id,
                prediction_episode_id=prediction_episode_id,
                output=output,
                created_at=now,
            )

        recommendation_instance_id = self._create_recommendation_instance(
            connection,
            actor=actor,
            session=session,
            prediction_episode_id=prediction_episode_id,
            projected=projected,
            profile=profile,
            now=now,
        )

        outcome_request_id = outcomes.create_outcome_request(
            connection,
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            prediction_episode_id=prediction_episode_id,
            target_definition_version=target_row["target_definition_version"],
            target_start_at=now,
            target_end_at=target_end_at,
            capture_deadline_at=capture_deadline_at,
            eligible_reporter_roles=tuple(
                str(role) for role in _roles(target_row["eligible_reporter_roles"])
            ),
            created_at=now,
        )
        outcomes.materialize_resolution(
            connection,
            tenant_id=actor.tenant_id,
            prediction_episode_id=prediction_episode_id,
            target_start_at=now,
            target_end_at=target_end_at,
            capture_deadline_at=capture_deadline_at,
            now=now,
        )
        return SubmitFormSessionView(
            form_session_id=session["form_session_id"],
            status=SubmitStatus.EPISODE_CREATED.value,
            submitted_at=now,
            prediction_episode_id=prediction_episode_id,
            outcome_request_id=outcome_request_id,
            recommendation_instance_id=recommendation_instance_id,
        )

    def _create_recommendation_instance(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        session: sqlite3.Row,
        prediction_episode_id: str,
        projected: tuple[dict[str, Any], ...],
        profile: dict[str, Any] | None,
        now: str,
    ) -> str:
        """SPEC 10.1: la instancia y su intent se persisten con el episodio."""
        scenario = self._services.ports.form.build_scenario(
            tenant_id=actor.tenant_id,
            subject_id=session["subject_id"],
            form_session_id=session["form_session_id"],
            source=session["source"],
            observations=projected,
            profile=profile,
            schema_version=SCENARIO_SCHEMA_VERSION,
        )
        payload = scenario.as_payload()
        scenario_hash = keyed_scenario_hash(
            self._services.settings.scenario_secret, scenario.schema_version, payload
        )
        availability = catalog.derive_availability(
            connection, tenant_id=actor.tenant_id, cutoff=now
        )

        if not scenario.available:
            return recommendations.create_instance(
                connection,
                recommendations.NewInstance(
                    tenant_id=actor.tenant_id,
                    subject_id=session["subject_id"],
                    prediction_episode_id=prediction_episode_id,
                    scenario_hash=scenario_hash,
                    scenario_schema_version=scenario.schema_version,
                    scenario_builder_version=scenario.builder_version,
                    scenario_payload=payload,
                    catalog_version=None,
                    corpus_version=None,
                    strategy_version_ids=(),
                    runtime_status=RuntimeStatus.ABSTAINED.value,
                    abstention_reasons=(scenario.abstention_reason or "scenario_unavailable",),
                    availability_reason=availability.reason.value,
                    created_at=now,
                    cipher_key=self._services.settings.scenario_secret,
                ),
            )

        if not availability.ready or availability.catalog_version is None:
            return recommendations.create_instance(
                connection,
                recommendations.NewInstance(
                    tenant_id=actor.tenant_id,
                    subject_id=session["subject_id"],
                    prediction_episode_id=prediction_episode_id,
                    scenario_hash=scenario_hash,
                    scenario_schema_version=scenario.schema_version,
                    scenario_builder_version=scenario.builder_version,
                    scenario_payload=payload,
                    catalog_version=None,
                    corpus_version=availability.corpus_version,
                    strategy_version_ids=(),
                    runtime_status=RuntimeStatus.ABSTAINED.value,
                    abstention_reasons=(availability.reason.value,),
                    availability_reason=availability.reason.value,
                    created_at=now,
                    cipher_key=self._services.settings.scenario_secret,
                ),
            )

        snapshot = catalog.load_snapshot(
            connection,
            tenant_id=actor.tenant_id,
            catalog_version=availability.catalog_version,
            cutoff=now,
        )
        decision = self._services.ports.rag.recommend(
            tenant_id=actor.tenant_id,
            scenario=payload,
            catalog=snapshot,
            as_of_at=now,
        )
        matched = decision.status == RuntimeStatus.MATCHED.value
        recommendation_instance_id = recommendations.create_instance(
            connection,
            recommendations.NewInstance(
                tenant_id=actor.tenant_id,
                subject_id=session["subject_id"],
                prediction_episode_id=prediction_episode_id,
                scenario_hash=scenario_hash,
                scenario_schema_version=scenario.schema_version,
                scenario_builder_version=scenario.builder_version,
                scenario_payload=payload,
                catalog_version=availability.catalog_version,
                corpus_version=availability.corpus_version,
                strategy_version_ids=tuple(
                    strategy.strategy_version_id for strategy in decision.strategies
                ),
                runtime_status=decision.status,
                abstention_reasons=decision.abstention_reasons,
                availability_reason=availability.reason.value,
                created_at=now,
                cipher_key=self._services.settings.scenario_secret,
            ),
        )
        if not matched and decision.authoring_request_intent:
            recommendations.create_authoring_request(
                connection,
                tenant_id=actor.tenant_id,
                subject_id=session["subject_id"],
                prediction_episode_id=prediction_episode_id,
                scenario_hash=scenario_hash,
                scenario_schema_version=scenario.schema_version,
                scenario_payload=payload,
                reason=decision.intent_reason or "no_approved_match",
                catalog_version=availability.catalog_version,
                created_at=now,
                cipher_key=self._services.settings.scenario_secret,
            )
        return recommendation_instance_id

    # -- lectura ---------------------------------------------------------

    def view(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        form_session_id: str,
        now: str,
    ) -> FormSessionView:
        session = self._session(connection, actor=actor, form_session_id=form_session_id)
        pending = self._pending_outcome(connection, actor=actor, session=session, now=now)
        if session["status"] == FormSessionStatus.DRAFT.value:
            plan = form_plan.build_and_persist(
                connection,
                ports=self._services.ports,
                session=session,
                now=now,
                outcome_pending=pending is not None,
            )
        else:
            # Una sesión cerrada muestra lo que realmente se presentó.
            plan = form_plan.stored_plan(connection, session=session)
        highlighted, tail = form_plan.question_views(
            connection, plan=plan, form_session_id=form_session_id
        )
        return FormSessionView(
            form_session_id=session["form_session_id"],
            subject_id=session["subject_id"],
            source=session["source"],
            session_kind=session["session_kind"],
            status=session["status"],
            opened_at=session["opened_at"],
            submitted_at=session["submitted_at"],
            audit_mode=bool(session["audit_mode"]),
            form_policy_version=session["form_policy_version"],
            voi_status=plan.voi_status,
            plan_source=plan.plan_source,
            outcome_pending=pending,
            highlighted=highlighted,
            tail=tail,
            answered_field_codes=list(
                sessions_store.answered_field_codes(connection, form_session_id)
            ),
        )

    def _pending_outcome(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        session: sqlite3.Row,
        now: str,
    ):
        row = connection.execute(
            "SELECT * FROM outcome_requests WHERE tenant_id = ? AND subject_id = ?"
            " AND capture_deadline_at >= ? ORDER BY created_at DESC LIMIT 1",
            (actor.tenant_id, session["subject_id"], now),
        ).fetchone()
        if row is None:
            return None
        resolution = outcomes.active_resolution(connection, row["prediction_episode_id"])
        if resolution is None or resolution["status"] != OutcomeResolutionStatus.PENDING.value:
            return None
        if not any(actor.has_role(role) for role in outcomes.eligible_reporter_roles(row)):
            return None
        target_row = identity.target_definition(connection, row["target_definition_version"])
        if target_row is None:
            return None
        state = outcomes.derive_request_status(
            resolution_status=resolution["status"],
            capture_deadline_at=row["capture_deadline_at"],
            now=now,
        )
        return form_plan.outcome_block(
            connection, request_row=row, target_row=target_row, state=state.value
        )

    def _session(
        self, connection: sqlite3.Connection, *, actor: ActorContext, form_session_id: str
    ) -> sqlite3.Row:
        row = sessions_store.session(connection, form_session_id)
        if row is None or row["tenant_id"] != actor.tenant_id:
            raise not_found()
        return row

    def _session_for_write(
        self, connection: sqlite3.Connection, *, actor: ActorContext, form_session_id: str
    ) -> sqlite3.Row:
        row = self._session(connection, actor=actor, form_session_id=form_session_id)
        if row["status"] != FormSessionStatus.DRAFT.value:
            raise invalid("form_session_not_open")
        return row


def _origin_for(cohort_kind: str) -> DataOrigin:
    """SPEC 5.6: cohorte y origen no se intercambian, pero sí se corresponden."""
    return DataOrigin.SYNTHETIC if cohort_kind == CohortKind.DEMO_FIXTURE.value else DataOrigin.REAL


def _roles(raw: str) -> list[str]:
    return [str(item) for item in load_list(raw)]
