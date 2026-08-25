"""Lectura de reportes de evaluación (SPEC 14, TAREAS P2.9-P2.10).

La API no entrena ni evalúa: importa lo que `tools/train` produjo y lo sirve con
origen, dataset hash, modelo, estimabilidad y limitaciones visibles.
"""

from __future__ import annotations

import sqlite3

from apps.api.auth.context import ActorContext
from apps.api.contracts.enums import (
    AccreditationCapability,
    DataOrigin,
    IntendedUse,
    Role,
)
from apps.api.contracts.models import EvaluationReportView, MetricView
from apps.api.errors import AuditIntent, forbidden, not_found
from apps.api.services.base import Services
from apps.api.store import audit
from apps.api.store import evaluation as evaluation_store
from apps.api.store.json_columns import load_list


class EvaluationService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def get(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        model_version: str,
        now: str,
    ) -> EvaluationReportView:
        """SPEC 13.1: `model_evaluator` o professional acreditado."""
        capability = (
            AccreditationCapability.MODEL_EVALUATION
            if actor.has_role(Role.MODEL_EVALUATOR)
            else AccreditationCapability.SUBJECT_CARE
        )
        if not actor.has_any_role(Role.MODEL_EVALUATOR, Role.PROFESSIONAL):
            self._deny(
                connection,
                actor=actor,
                model_version=model_version,
                now=now,
                reason="role_not_allowed",
            )
        accreditation = self._services.authorization.active_accreditation(
            connection, actor=actor, capability=capability, cutoff=now
        )
        if accreditation is None:
            self._deny(
                connection,
                actor=actor,
                model_version=model_version,
                now=now,
                reason="accreditation_required",
            )

        report = evaluation_store.published_report(
            connection, tenant_id=actor.tenant_id, model_version=model_version
        )
        if report is None:
            raise not_found("evaluation_not_found")

        audit.record(
            connection,
            actor=actor,
            action="evaluation_read",
            resource_type="evaluation_report",
            resource_id=report["evaluation_report_id"],
            decision="allowed",
            occurred_at=now,
            request_id=actor.request_id,
        )
        return EvaluationReportView(
            evaluation_report_id=report["evaluation_report_id"],
            model_version=report["model_version"],
            track_id=report["track_id"],
            model_state=report["state"],
            intended_use=report["intended_use"],
            data_origin=report["data_origin"],
            dataset_sha256=report["dataset_sha256"],
            target_definition_version=report["target_definition_version"],
            protocol_version=report["protocol_version"],
            metrics=[MetricView(**metric) for metric in report["metrics"]],
            abstention_by_reason=report["abstention_by_reason"],
            limitations_es=[str(item) for item in load_list(report["limitations_es"])],
            published_at=report["published_at"],
            # SPEC 14.3 / INV-34: las métricas sintéticas llevan `simulation_only`.
            simulation_only=(
                report["data_origin"] == DataOrigin.SYNTHETIC.value
                or report["intended_use"] == IntendedUse.SIMULATION_ONLY.value
            ),
        )

    def _deny(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        model_version: str,
        now: str,
        reason: str,
    ) -> None:
        raise forbidden(
            reason,
            audit=AuditIntent(
                action="evaluation_read",
                resource_type="evaluation_report",
                decision="denied",
                reason_code=reason,
                tenant_id=actor.tenant_id,
                actor_id=actor.actor_id,
                resource_id=model_version,
                request_id=actor.request_id,
            ),
        )
