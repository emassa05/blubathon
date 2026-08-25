"""Servicio de recomendaciones, revisión profesional y ejecución.

SPEC 9.8, 10.1-10.4, 11.6 y CONVENTIONS 12.1.

Separaciones que este servicio no mezcla:

- `RecommendationReview` es preferencia profesional.
- `HumanPlanVersion` es texto humano sustituto, sin citas RAG.
- `StrategyExecution` es exposición real, con su propio orden temporal.
- El outcome vive en otra entidad y no se infiere de ninguna de las anteriores.

Un GET nunca crea filas: la instancia y su intent se persistieron al crear el
episodio.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from apps.api.auth.context import ActorContext
from apps.api.canonical import canonical_timestamp
from apps.api.contracts.enums import (
    AccreditationCapability,
    ExecutionStatus,
    GrantCapability,
    NonActionableReason,
    RecommendationResponseStatus,
    ReviewDecision,
    ReviewStatus,
    Role,
    RuntimeStatus,
)
from apps.api.contracts.models import (
    CitationView,
    ExecutionView,
    HumanPlanItemView,
    RecommendationInboxView,
    RecommendationInstanceSummary,
    RecommendationItemView,
    RecommendationReviewRequest,
    RecommendationReviewResponse,
    RecommendationsView,
    ScenarioV1,
    StrategyExecutionRequest,
    StrategyItemView,
)
from apps.api.errors import (
    AuditIntent,
    conflict,
    forbidden,
    invalid,
    not_found,
    precondition_required,
)
from apps.api.services.base import Services
from apps.api.store import audit, catalog, episodes, outcomes
from apps.api.store import recommendations as store
from apps.api.store.json_columns import load_list
from apps.api.store.sealing import unseal

PENDING = "pending"


class RecommendationService:
    def __init__(self, services: Services) -> None:
        self._services = services

    # -- lectura del cuidador y del profesional ---------------------------

    def for_episode(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        prediction_episode_id: str,
        now: str,
    ) -> RecommendationsView:
        episode = episodes.episode(connection, prediction_episode_id)
        if episode is None or episode["tenant_id"] != actor.tenant_id:
            raise not_found()
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=episode["subject_id"],
            capability=GrantCapability.SUBJECT_READ,
            cutoff=now,
            action="recommendation_read",
        )
        instance = store.instance_for_episode(connection, prediction_episode_id)
        if instance is None:
            raise not_found()
        return self._serialize(connection, actor=actor, instance=instance, now=now)

    def _serialize(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        instance: sqlite3.Row,
        now: str,
    ) -> RecommendationsView:
        revision = store.revision_etag(
            connection,
            recommendation_instance_id=instance["recommendation_instance_id"],
            cutoff=now,
        )
        if instance["runtime_status"] == RuntimeStatus.ABSTAINED.value:
            return RecommendationsView(
                status=RecommendationResponseStatus.ABSTAINED.value,
                recommendation_instance_id=instance["recommendation_instance_id"],
                catalog_version=instance["catalog_version"],
                corpus_version=instance["corpus_version"],
                reasons=[str(item) for item in load_list(instance["abstention_reasons"])],
                items=[],
                revision=revision,
            )

        reviews = store.active_reviews(
            connection,
            recommendation_instance_id=instance["recommendation_instance_id"],
            cutoff=now,
        )
        executions = {
            row["strategy_version_id"] or row["human_plan_version_id"]: row
            for row in store.active_executions(
                connection,
                recommendation_instance_id=instance["recommendation_instance_id"],
                cutoff=now,
            )
        }
        # El serializer aplica actor y grants: nunca se filtra solo en frontend.
        is_professional = actor.has_role(Role.PROFESSIONAL)
        items: list[RecommendationItemView] = []

        for strategy_version_id in store.instance_strategy_ids(instance):
            strategy = connection.execute(
                "SELECT * FROM strategy_versions WHERE strategy_version_id = ?",
                (strategy_version_id,),
            ).fetchone()
            if strategy is None:
                continue
            active = reviews.get(strategy_version_id)
            decision = None if active is None else active["decision"]
            dependencies_ok = catalog.dependencies_active(
                connection,
                strategy_version_id=strategy_version_id,
                catalog_version=instance["catalog_version"],
                cutoff=now,
            )
            non_actionable = (
                None if dependencies_ok else NonActionableReason.DEPENDENCY_SUSPENDED.value
            )

            if decision == ReviewDecision.HUMAN_PLAN_SUBSTITUTED.value:
                plan = store.human_plan(connection, active["human_plan_version_id"])
                if plan is None:
                    continue
                # SPEC 10.2: un plan humano existe porque una review lo sustituyó;
                # su `review_status` es siempre `human_plan_substituted`.
                item = HumanPlanItemView(
                    human_plan_version_id=plan["human_plan_version_id"],
                    strategy_version_id=(strategy_version_id if is_professional else None),
                    action_text_es=plan["action_text_es"],
                    required_approver_role=strategy["required_approver_role"],
                    allowed_executor_roles=[
                        str(role) for role in load_list(plan["allowed_executor_roles"])
                    ],
                    # SPEC 10.2 / INV-29: un plan humano no hereda las citas RAG.
                    citations=[],
                    non_actionable=non_actionable,
                    execution_status=_execution_status(
                        executions.get(plan["human_plan_version_id"])
                    ),
                )
            else:
                item = StrategyItemView(
                    review_status=decision or PENDING,
                    strategy_version_id=strategy_version_id,
                    action_text_es=strategy["action_text_es"],
                    required_approver_role=strategy["required_approver_role"],
                    allowed_executor_roles=[
                        str(role) for role in load_list(strategy["allowed_executor_roles"])
                    ],
                    citations=_citations(connection, strategy_version_id),
                    non_actionable=non_actionable,
                    execution_status=_execution_status(executions.get(strategy_version_id)),
                )

            if is_professional:
                items.append(item)
                continue
            # La familia solo ve estrategias aprobadas o planes sustituidos, y
            # solo si las dependencias siguen activas.
            if store.is_favourable(decision or "") and non_actionable is None:
                items.append(item)

        if not items and not is_professional:
            return RecommendationsView(
                status=RecommendationResponseStatus.AWAITING_PROFESSIONAL_REVIEW.value,
                recommendation_instance_id=instance["recommendation_instance_id"],
                catalog_version=instance["catalog_version"],
                corpus_version=instance["corpus_version"],
                items=[],
                revision=revision,
            )
        return RecommendationsView(
            status=RecommendationResponseStatus.MATCHED.value,
            recommendation_instance_id=instance["recommendation_instance_id"],
            catalog_version=instance["catalog_version"],
            corpus_version=instance["corpus_version"],
            items=items,
            revision=revision,
        )

    # -- inbox profesional ------------------------------------------------

    def inbox(
        self, connection: sqlite3.Connection, *, actor: ActorContext, now: str
    ) -> RecommendationInboxView:
        if not actor.has_role(Role.PROFESSIONAL):
            raise forbidden("role_not_allowed")
        accreditation = self._services.authorization.active_accreditation(
            connection,
            actor=actor,
            capability=AccreditationCapability.SUBJECT_CARE,
            cutoff=now,
        )
        if accreditation is None:
            raise forbidden("accreditation_required")
        subject_ids = self._services.authorization.granted_subject_ids(
            connection,
            actor=actor,
            capability=GrantCapability.RECOMMENDATION_REVIEW,
            cutoff=now,
        )
        rows = store.pending_instance_ids(
            connection, tenant_id=actor.tenant_id, subject_ids=subject_ids, cutoff=now
        )
        items: list[RecommendationInstanceSummary] = []
        for instance in rows:
            reviews = store.active_reviews(
                connection,
                recommendation_instance_id=instance["recommendation_instance_id"],
                cutoff=now,
            )
            pending_ids = [
                strategy_version_id
                for strategy_version_id in store.instance_strategy_ids(instance)
                if strategy_version_id not in reviews
            ]
            if not pending_ids:
                continue
            subject = connection.execute(
                "SELECT display_label FROM subjects WHERE subject_id = ?",
                (instance["subject_id"],),
            ).fetchone()
            items.append(
                RecommendationInstanceSummary(
                    recommendation_instance_id=instance["recommendation_instance_id"],
                    prediction_episode_id=instance["prediction_episode_id"],
                    subject_id=instance["subject_id"],
                    subject_label="" if subject is None else subject["display_label"],
                    scenario_hash=instance["scenario_hash"],
                    strategy_version_ids=store.instance_strategy_ids(instance),
                    # El inbox solo lista instancias con estrategias sin revisar.
                    review_status=ReviewStatus.PENDING.value,
                    created_at=instance["created_at"],
                    catalog_version=instance["catalog_version"],
                    corpus_version=instance["corpus_version"],
                    runtime_status=instance["runtime_status"],
                    scenario=self._scenario_view(instance=instance),
                    pending_strategy_version_ids=pending_ids,
                    revision=store.revision_etag(
                        connection,
                        recommendation_instance_id=instance["recommendation_instance_id"],
                        cutoff=now,
                    ),
                )
            )
        return RecommendationInboxView(items=items)

    def _scenario_view(self, *, instance: sqlite3.Row) -> ScenarioV1 | None:
        """El escenario que ve el profesional viene de la instancia persistida.

        No contiene identidad, notas ni historial (SPEC 9.7): es la copia
        cifrada que la instancia guardó al crearse. Si no hay copia legible se
        devuelve `None` en vez de inventar contenido.
        """
        payload = unseal(instance["encrypted_scenario"], self._services.settings.scenario_secret)
        if payload is None:
            return None
        return ScenarioV1(
            schema_version=payload.get("schema_version", instance["scenario_schema_version"]),
            field_values=payload.get("field_values", {}),
            context_tags=payload.get("context_tags", []),
            profile_tags=payload.get("profile_tags", []),
            contraindication_tags=payload.get("contraindication_tags", []),
        )

    # -- reautorización de replay -----------------------------------------

    def authorize_instance(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        recommendation_instance_id: str,
        capability: GrantCapability,
        now: str,
    ) -> None:
        instance = self._instance(
            connection, actor=actor, recommendation_instance_id=recommendation_instance_id
        )
        allowed_roles = (
            (Role.PROFESSIONAL,)
            if capability is GrantCapability.RECOMMENDATION_REVIEW
            else (Role.CAREGIVER, Role.PROFESSIONAL)
        )
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=instance["subject_id"],
            capability=capability,
            cutoff=now,
            action="recommendation_replay",
            allowed_roles=allowed_roles,
        )

    # -- revisión ---------------------------------------------------------

    def create_review(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        recommendation_instance_id: str,
        request: RecommendationReviewRequest,
        if_match: str | None,
        now: str,
    ) -> RecommendationReviewResponse:
        instance = self._instance(
            connection, actor=actor, recommendation_instance_id=recommendation_instance_id
        )
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=instance["subject_id"],
            capability=GrantCapability.RECOMMENDATION_REVIEW,
            cutoff=now,
            action="recommendation_review",
            allowed_roles=(Role.PROFESSIONAL,),
        )
        self._check_revision(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            if_match=if_match,
            now=now,
        )

        strategy_version_id = str(request.strategy_version_id)
        reviews_now = store.active_reviews(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            cutoff=now,
        )
        if strategy_version_id not in store.instance_strategy_ids(instance):
            raise invalid("validation_error", reason="strategy_not_in_instance")
        strategy = connection.execute(
            "SELECT * FROM strategy_versions WHERE strategy_version_id = ?",
            (strategy_version_id,),
        ).fetchone()
        if strategy is None:
            raise not_found()

        decision = ReviewDecision(request.decision)
        favourable = store.is_favourable(decision.value)
        if favourable:
            # SPEC 10.2: aprobar o sustituir exige cumplir `required_approver_role`.
            if not actor.has_role(strategy["required_approver_role"]):
                raise forbidden(
                    "review_role_not_permitted",
                    audit=AuditIntent(
                        action="recommendation_review",
                        resource_type="recommendation_instance",
                        decision="denied",
                        reason_code="review_role_not_permitted",
                        tenant_id=actor.tenant_id,
                        actor_id=actor.actor_id,
                        resource_id=recommendation_instance_id,
                        subject_id=instance["subject_id"],
                        request_id=actor.request_id,
                    ),
                )
            if not catalog.dependencies_active(
                connection,
                strategy_version_id=strategy_version_id,
                catalog_version=instance["catalog_version"],
                cutoff=now,
            ):
                raise conflict("recommendation_dependency_suspended")

        # CONVENTIONS 8.1: una revisión se corrige apilando otra que enlaza la
        # activa. El contrato no lleva `supersedes_id`, así que el enlace lo
        # deriva el servidor a partir de la revisión vigente de esa estrategia.
        previous = reviews_now.get(strategy_version_id)
        supersedes_id = None if previous is None else str(previous["review_id"])

        human_plan_version_id: str | None = None
        if decision is ReviewDecision.HUMAN_PLAN_SUBSTITUTED:
            # `RecommendationReviewRequest` ya exige texto y roles al sustituir.
            allowed = {str(role) for role in load_list(strategy["allowed_executor_roles"])}
            requested = {str(role) for role in (request.human_plan_allowed_executor_roles or ())}
            if not requested <= allowed:
                raise invalid("human_plan_roles_not_subset")
            human_plan_version_id = store.create_human_plan(
                connection,
                tenant_id=actor.tenant_id,
                recommendation_instance_id=recommendation_instance_id,
                replaced_strategy_version_id=strategy_version_id,
                action_text_es=request.human_plan_action_text_es or "",
                author_actor_id=actor.actor_id,
                allowed_executor_roles=tuple(sorted(requested)),
                created_at=now,
            )

        review_id = store.insert_review(
            connection,
            store.NewReview(
                tenant_id=actor.tenant_id,
                recommendation_instance_id=recommendation_instance_id,
                strategy_version_id=strategy_version_id,
                decision=decision.value,
                reviewed_by=actor.actor_id,
                reviewer_role=strategy["required_approver_role"]
                if favourable
                else Role.PROFESSIONAL.value,
                reviewed_at=now,
                human_plan_version_id=human_plan_version_id,
                supersedes_id=supersedes_id,
                ingested_at=now,
            ),
        )
        audit.record(
            connection,
            actor=actor,
            action="recommendation_review",
            resource_type="recommendation_review",
            resource_id=review_id,
            subject_id=instance["subject_id"],
            decision="allowed",
            reason_code=decision.value,
            occurred_at=now,
            request_id=actor.request_id,
        )
        row = store.review(connection, review_id)
        assert row is not None
        return RecommendationReviewResponse(
            review_id=row["review_id"],
            recommendation_instance_id=row["recommendation_instance_id"],
            strategy_version_id=row["strategy_version_id"],
            decision=row["decision"],
            reviewed_at=row["reviewed_at"],
            human_plan_version_id=row["human_plan_version_id"],
        )

    # -- ejecución --------------------------------------------------------

    def create_execution(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        recommendation_instance_id: str,
        request: StrategyExecutionRequest,
        if_match: str | None,
        now: str,
    ) -> ExecutionView:
        instance = self._instance(
            connection, actor=actor, recommendation_instance_id=recommendation_instance_id
        )
        self._services.authorization.authorize_subject(
            connection,
            actor=actor,
            subject_id=instance["subject_id"],
            capability=GrantCapability.EXECUTION_RECORD,
            cutoff=now,
            action="strategy_execution",
        )
        self._check_revision(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            if_match=if_match,
            now=now,
        )

        strategy_version_id = (
            None if request.strategy_version_id is None else str(request.strategy_version_id)
        )
        human_plan_version_id = (
            None if request.human_plan_version_id is None else str(request.human_plan_version_id)
        )
        if (strategy_version_id is None) == (human_plan_version_id is None):
            raise invalid("execution_target_ambiguous")

        reviews = store.active_reviews(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            cutoff=now,
        )
        if strategy_version_id is not None:
            strategy = connection.execute(
                "SELECT * FROM strategy_versions WHERE strategy_version_id = ?",
                (strategy_version_id,),
            ).fetchone()
            if strategy is None or strategy_version_id not in store.instance_strategy_ids(instance):
                raise not_found()
            active = reviews.get(strategy_version_id)
            if active is None or active["decision"] != ReviewDecision.APPROVED.value:
                raise conflict("revision_conflict", reason="strategy_not_approved")
            allowed_roles = {str(role) for role in load_list(strategy["allowed_executor_roles"])}
            if not catalog.dependencies_active(
                connection,
                strategy_version_id=strategy_version_id,
                catalog_version=instance["catalog_version"],
                cutoff=now,
            ):
                raise conflict("recommendation_dependency_suspended")
        else:
            plan = store.human_plan(connection, human_plan_version_id or "")
            if plan is None or plan["recommendation_instance_id"] != recommendation_instance_id:
                raise not_found()
            active = reviews.get(plan["replaced_strategy_version_id"])
            if (
                active is None
                or active["decision"] != ReviewDecision.HUMAN_PLAN_SUBSTITUTED.value
                or active["human_plan_version_id"] != human_plan_version_id
            ):
                raise conflict("revision_conflict", reason="human_plan_not_active")
            allowed_roles = {str(role) for role in load_list(plan["allowed_executor_roles"])}

        actor_role = next((role for role in sorted(allowed_roles) if actor.has_role(role)), None)
        if actor_role is None:
            raise forbidden(
                "execution_role_not_permitted",
                audit=AuditIntent(
                    action="strategy_execution",
                    resource_type="recommendation_instance",
                    decision="denied",
                    reason_code="execution_role_not_permitted",
                    tenant_id=actor.tenant_id,
                    actor_id=actor.actor_id,
                    resource_id=recommendation_instance_id,
                    subject_id=instance["subject_id"],
                    request_id=actor.request_id,
                ),
            )

        status = ExecutionStatus(request.status)
        applied_at = None if request.applied_at is None else canonical_timestamp(request.applied_at)
        if status is ExecutionStatus.APPLIED and applied_at is None:
            raise invalid("validation_error", reason="applied_at_required")
        if applied_at is not None and applied_at > now:
            raise invalid("validation_error", reason="applied_at_in_the_future")
        if status is not ExecutionStatus.APPLIED and applied_at is not None:
            raise invalid("validation_error", reason="applied_at_requires_applied")

        # Igual que una revisión: la corrección apila una fila nueva enlazada a
        # la vigente, y el enlace lo deriva el servidor.
        supersedes_id = store.active_execution_id(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            strategy_version_id=strategy_version_id,
            human_plan_version_id=human_plan_version_id,
            cutoff=now,
        )

        strategy_execution_id = store.insert_execution(
            connection,
            store.NewExecution(
                tenant_id=actor.tenant_id,
                recommendation_instance_id=recommendation_instance_id,
                strategy_version_id=strategy_version_id,
                human_plan_version_id=human_plan_version_id,
                status=status.value,
                actor_id=actor.actor_id,
                actor_role=actor_role,
                recorded_at=now,
                applied_at=applied_at,
                supersedes_id=supersedes_id,
                ingested_at=now,
            ),
        )
        audit.record(
            connection,
            actor=actor,
            action="strategy_execution",
            resource_type="strategy_execution",
            resource_id=strategy_execution_id,
            subject_id=instance["subject_id"],
            decision="allowed",
            reason_code=status.value,
            occurred_at=now,
            request_id=actor.request_id,
        )
        row = store.execution(connection, strategy_execution_id)
        assert row is not None
        return ExecutionView(
            strategy_execution_id=row["strategy_execution_id"],
            recommendation_instance_id=row["recommendation_instance_id"],
            strategy_version_id=row["strategy_version_id"],
            human_plan_version_id=row["human_plan_version_id"],
            status=row["status"],
            recorded_at=row["recorded_at"],
            applied_at=row["applied_at"],
            exposure_eligible=self._exposure_eligible(
                connection, instance=instance, execution=row, review=active
            ),
        )

    # -- soporte ----------------------------------------------------------

    def _exposure_eligible(
        self,
        connection: sqlite3.Connection,
        *,
        instance: sqlite3.Row,
        execution: sqlite3.Row,
        review: dict[str, Any] | None,
    ) -> bool:
        """SPEC 10.3. Una aplicación tardía se conserva, pero no se atribuye."""
        if execution["status"] != ExecutionStatus.APPLIED.value or review is None:
            return False
        applied_at = execution["applied_at"]
        if not (instance["created_at"] <= review["reviewed_at"] <= applied_at):
            return False
        episode = episodes.episode(connection, instance["prediction_episode_id"])
        if episode is None or applied_at > episode["target_end_at"]:
            return False
        resolution = outcomes.active_resolution(connection, instance["prediction_episode_id"])
        if resolution is not None and resolution["status"] == "yes":
            report = outcomes.report(connection, resolution["qualifying_report_id"])
            if (
                report is not None
                and report["occurred_at"] is not None
                and applied_at >= report["occurred_at"]
            ):
                return False
        return True

    def _instance(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        recommendation_instance_id: str,
    ) -> sqlite3.Row:
        row = store.instance(connection, recommendation_instance_id)
        if row is None or row["tenant_id"] != actor.tenant_id:
            raise not_found()
        return row

    def _check_revision(
        self,
        connection: sqlite3.Connection,
        *,
        recommendation_instance_id: str,
        if_match: str | None,
        now: str,
    ) -> None:
        """SPEC 11.2: los recursos con revisión usan `If-Match` y 409 en conflicto."""
        if if_match is None:
            raise precondition_required()
        current = store.revision_etag(
            connection,
            recommendation_instance_id=recommendation_instance_id,
            cutoff=now,
        )
        if if_match.strip('"') != current:
            raise conflict("revision_conflict")


def _citations(connection: sqlite3.Connection, strategy_version_id: str) -> list[CitationView]:
    rows = connection.execute(
        "SELECT * FROM strategy_citations WHERE strategy_version_id = ?"
        " ORDER BY claim_id, citation_id",
        (strategy_version_id,),
    ).fetchall()
    return [
        CitationView(
            citation_id=row["citation_id"],
            claim_id=row["claim_id"],
            locator=row["locator"],
            quoted_text=row["quoted_text"],
            canonical_url=row["canonical_url"],
        )
        for row in rows
    ]


def _execution_status(row: dict[str, Any] | None) -> str | None:
    return None if row is None else row["status"]
