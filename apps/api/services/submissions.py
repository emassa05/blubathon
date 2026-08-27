"""Stateless form planning and atomic submissions."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta

from apps.api.canonical import canonical_timestamp, parse_timestamp
from apps.api.contracts.constants import (
    FORM_POLICY_VERSION,
    OUTCOME_CAPTURE_LIMIT_HOURS,
    TARGET_HORIZON_HOURS,
)
from apps.api.contracts.enums import (
    CohortKind,
    DataOrigin,
    EntryMode,
    SubmitStatus,
    TrackId,
)
from apps.api.contracts.field_catalog import applicable_fields, validate_field_value
from apps.api.contracts.models import (
    AnswerItem,
    FormPlanResponse,
    FormSubmissionResponse,
)
from apps.api.errors import invalid, not_found
from apps.api.services import form_plan
from apps.api.services.base import Services
from apps.api.services.local_time import REFERENCE_ZONE
from apps.api.services.local_time import local_date as reference_date
from apps.api.services.recommendation_query import query_for, risk_band_for
from apps.api.store import episodes, identity, outcomes, recommendations
from apps.api.store import form_sessions as submissions_store
from tools.seed import ids


class SubmissionService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def build_plan(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        answers: dict,
        now: str,
    ) -> FormPlanResponse:
        self._subject(tenant_id, subject_id)
        return form_plan.build(
            ports=self._services.ports,
            tenant_id=tenant_id,
            subject_id=subject_id,
            source=_stored_source(source),
            answers=answers,
            now=now,
        )

    def submit(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        local_date: str,
        answers: tuple[AnswerItem, ...],
        now: str,
    ) -> FormSubmissionResponse:
        subject = identity.subject(connection, subject_id)
        if subject is None or subject["tenant_id"] != tenant_id:
            raise not_found()
        stored_source = _stored_source(source)
        effective_at = _effective_at_for(local_date, now)
        allowed = set(applicable_fields(stored_source))
        submission_id = submissions_store.create_submission(
            connection,
            submissions_store.NewSession(
                tenant_id=tenant_id,
                subject_id=subject_id,
                actor_id=str(ids.CAREGIVER_A),
                source=stored_source,
                session_kind="caregiver_daily",
                audit_mode=False,
                audit_bucket=0,
                form_policy_version=FORM_POLICY_VERSION,
                local_date=local_date,
                opened_at=now,
            ),
        )
        for answer in answers:
            if answer.interaction == "unknown":
                continue
            if str(answer.field_code) not in allowed:
                raise invalid("field_not_allowed_for_source", field_code=answer.field_code)
            value = validate_field_value(answer.field_code, answer.value)
            submissions_store.insert_observation(
                connection,
                submissions_store.NewObservation(
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    form_session_id=submission_id,
                    field_code=str(answer.field_code),
                    value=value,
                    source=stored_source,
                    actor_id=str(ids.CAREGIVER_A),
                    entry_mode=_entry_mode(answer.interaction),
                    data_origin=_origin_for(subject["cohort_kind"]),
                    cohort_kind=subject["cohort_kind"],
                    effective_at=effective_at,
                    ingested_at=now,
                    local_date=local_date,
                ),
            )

        cohort = CohortKind(subject["cohort_kind"])
        scope = "demo_fixture" if cohort is CohortKind.DEMO_FIXTURE else "tenant"
        target, reason = identity.select_target_definition(
            connection,
            scope=scope,
            tenant_id=None if cohort is CohortKind.DEMO_FIXTURE else tenant_id,
            cutoff=now,
        )
        if target is None:
            submissions_store.set_submission_result(
                connection,
                form_session_id=submission_id,
                submitted_at=now,
                prediction_status=reason,
                prediction_episode_id=None,
                linked_prediction_episode_id=None,
            )
            return FormSubmissionResponse(
                submission_id=submission_id,
                status=SubmitStatus.TARGET_DEFINITION_UNAVAILABLE,
            )

        open_episode = submissions_store.open_primary_episode(
            connection, tenant_id=tenant_id, subject_id=subject_id, at=now
        )
        if open_episode is not None:
            episode_id = open_episode["prediction_episode_id"]
            submissions_store.set_submission_result(
                connection,
                form_session_id=submission_id,
                submitted_at=now,
                prediction_status=SubmitStatus.EPISODE_LINKED.value,
                prediction_episode_id=None,
                linked_prediction_episode_id=episode_id,
            )
            return FormSubmissionResponse(
                submission_id=submission_id,
                status=SubmitStatus.EPISODE_LINKED,
                prediction_episode_id=episode_id,
            )

        return self._create_episode(
            connection,
            tenant_id=tenant_id,
            subject=subject,
            submission_id=submission_id,
            target=target,
            answers=answers,
            now=now,
        )

    def _create_episode(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        subject: sqlite3.Row,
        submission_id: str,
        target: sqlite3.Row,
        answers: tuple[AnswerItem, ...],
        now: str,
    ) -> FormSubmissionResponse:
        subject_id = subject["subject_id"]
        as_of = parse_timestamp(now)
        target_end_at = canonical_timestamp(as_of + timedelta(hours=TARGET_HORIZON_HOURS))
        deadline = canonical_timestamp(as_of + timedelta(hours=OUTCOME_CAPTURE_LIMIT_HOURS))
        origin = _origin_for(subject["cohort_kind"])
        profile = identity.active_profile(
            connection, tenant_id=tenant_id, subject_id=subject_id, cutoff=now
        )
        episode_id = episodes.create_primary_episode(
            connection,
            episodes.NewEpisode(
                tenant_id=tenant_id,
                subject_id=subject_id,
                form_session_id=submission_id,
                as_of_at=now,
                target_start_at=now,
                target_end_at=target_end_at,
                capture_deadline_at=deadline,
                target_definition_version=target["target_definition_version"],
                profile_version=None if profile is None else profile["profile_version"],
                care_mode=None if profile is None else profile["care_mode"],
                input_data_origin=origin,
                created_at=now,
            ),
        )
        submissions_store.set_submission_result(
            connection,
            form_session_id=submission_id,
            submitted_at=now,
            prediction_status=SubmitStatus.EPISODE_CREATED.value,
            prediction_episode_id=episode_id,
            linked_prediction_episode_id=None,
        )
        projected = submissions_store.projected_session_observations(
            connection, form_session_id=submission_id, cutoff=now
        )
        episodes.create_feature_snapshot(
            connection,
            tenant_id=tenant_id,
            prediction_episode_id=episode_id,
            as_of_at=now,
            input_data_origin=origin,
            projected_observation_ids=tuple(row["field_observation_id"] for row in projected),
            projected_outcome_ids=(),
            consent_ids=(),
            profile_version=None if profile is None else profile["profile_version"],
            care_mode=None if profile is None else profile["care_mode"],
            created_at=now,
        )
        probability = None
        for output in self._services.ports.prediction.predict(
            tenant_id=tenant_id,
            subject_id=subject_id,
            prediction_episode_id=episode_id,
            as_of_at=now,
            cohort_kind=subject["cohort_kind"],
            input_data_origin=origin,
            care_mode=None if profile is None else profile["care_mode"],
            target_definition_version=target["target_definition_version"],
            snapshot={"observation_ids": [row["field_observation_id"] for row in projected]},
        ):
            episodes.insert_prediction_output(
                connection,
                tenant_id=tenant_id,
                prediction_episode_id=episode_id,
                output=output,
                created_at=now,
            )
            if output.track_id == TrackId.REAL_PERSONAL_BASELINE_V1.value:
                probability = output.probability

        query_es = query_for(probability, answers)
        recommendation_id = recommendations.create_pending(
            connection,
            tenant_id=tenant_id,
            subject_id=subject_id,
            prediction_episode_id=episode_id,
            risk_band=risk_band_for(probability),
            query_es=query_es,
            now=now,
        )
        outcome_request_id = outcomes.create_outcome_request(
            connection,
            tenant_id=tenant_id,
            subject_id=subject_id,
            prediction_episode_id=episode_id,
            target_definition_version=target["target_definition_version"],
            target_start_at=now,
            target_end_at=target_end_at,
            capture_deadline_at=deadline,
            eligible_reporter_roles=(),
            created_at=now,
        )
        outcomes.materialize_resolution(
            connection,
            tenant_id=tenant_id,
            prediction_episode_id=episode_id,
            target_start_at=now,
            target_end_at=target_end_at,
            capture_deadline_at=deadline,
            now=now,
        )
        return FormSubmissionResponse(
            submission_id=submission_id,
            status=SubmitStatus.EPISODE_CREATED,
            prediction_episode_id=episode_id,
            recommendation_instance_id=recommendation_id,
            outcome_request_id=outcome_request_id,
        )

    def _subject(self, tenant_id: str, subject_id: str) -> sqlite3.Row:
        with self._services.database.read() as connection:
            subject = identity.subject(connection, subject_id)
            if subject is None or subject["tenant_id"] != tenant_id:
                raise not_found()
            return subject


def _stored_source(source: str) -> str:
    if source != "caregiver_daily":
        raise invalid("validation_error", reason="unsupported_source")
    return "home"


def _effective_at_for(local_date: str, now: str) -> str:
    """El instante efectivo de una respuesta, dentro del día que declara.

    `FieldObservation` exige que `local_date` sea la fecha en zona de referencia
    de `effective_at`, y aquí se escribían el día del formulario y el reloj del
    servidor sin compararlos. Al rellenar el cuestionario de un día pasado, la
    fila quedaba con el día de ayer y el instante de hoy: se guardaba sin
    protestar y hacía estallar la siguiente lectura del dominio.

    `effective_at` es tiempo clínico —cuándo fue cierto lo observado— y
    `ingested_at` tiempo de registro, que sigue siendo `now`. Rellenar ayer no
    cambia cuándo pasó, solo cuándo se anotó.
    """

    momento = parse_timestamp(now)
    dia = date.fromisoformat(local_date)
    hoy = reference_date(momento)
    if dia == hoy:
        return now
    if dia > hoy:
        # Sin instante posible dentro de un día que no ha llegado. Se rechaza
        # en vez de escribir una fila que el dominio no puede releer.
        raise invalid("local_date_in_future", local_date=local_date)
    fin_del_dia = datetime.combine(dia, time(23, 59, 59, 999000), tzinfo=REFERENCE_ZONE)
    return canonical_timestamp(fin_del_dia)


def _origin_for(cohort_kind: str) -> str:
    return (
        DataOrigin.SYNTHETIC.value
        if CohortKind(cohort_kind) is CohortKind.DEMO_FIXTURE
        else DataOrigin.REAL.value
    )


def _entry_mode(interaction: str) -> str:
    return {
        "manual": EntryMode.MANUAL_NO_DEFAULT.value,
        "accept_default": EntryMode.DEFAULT_ACCEPTED.value,
        "edit_default": EntryMode.DEFAULT_EDITED.value,
    }[interaction]
