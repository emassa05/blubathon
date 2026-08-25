"""Tenant, rol, acreditación, capability y grant (SPEC 13).

Regla dura de `SPEC 2.26`: tenant y rol no bastan. Toda operación clínica exige
un `SubjectAccessGrant` activo con la capability literal de la operación.

Las listas se filtran en SQL con :func:`granted_subject_ids` o con el fragmento
:data:`GRANT_FILTER_SQL`; nunca se cargan filas prohibidas para descartarlas
después (SPEC 13.2, CONVENTIONS 13).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from apps.api.auth.context import ActorContext
from apps.api.contracts.enums import (
    AccreditationCapability,
    AuthorizationStatus,
    CohortKind,
    ConsentPurpose,
    GrantCapability,
    Role,
)
from apps.api.errors import AuditIntent, forbidden, not_found
from apps.api.store import audit

# Un contrato de autorización está activo en un cutoff si su hoja proyectada
# tiene status active, la vigencia cubre el instante y no hay revocación
# efectiva (SPEC 13.1).
_ACTIVE_WINDOW = (
    f" status = '{AuthorizationStatus.ACTIVE.value}'"
    " AND valid_from <= :cutoff"
    " AND (valid_until IS NULL OR valid_until > :cutoff)"
    " AND (revoked_at IS NULL OR revoked_at > :cutoff)"
)

# Fragmento reutilizable: los sujetos sobre los que el actor tiene grant activo.
GRANT_FILTER_SQL = (
    "SELECT subject_id FROM subject_access_grants"
    " WHERE tenant_id = :tenant_id AND actor_id = :actor_id"
    f" AND {_ACTIVE_WINDOW}"
    " AND EXISTS (SELECT 1 FROM json_each(subject_access_grants.capabilities)"
    "            WHERE json_each.value = :capability)"
    " AND NOT EXISTS (SELECT 1 FROM subject_access_grants AS newer"
    "                 WHERE newer.supersedes_id ="
    "                       subject_access_grants.subject_access_grant_id"
    "                   AND newer.ingested_at <= :cutoff)"
)


@dataclass(frozen=True, slots=True)
class SubjectAuthorization:
    """Resultado de una comprobación completa sobre un sujeto."""

    subject_id: str
    tenant_id: str
    cohort_kind: str
    display_label: str
    grant_id: str
    capability: str
    accreditation_id: str | None


class AuthorizationService:
    def __init__(self, *, allowed_cohort: CohortKind) -> None:
        self._allowed_cohort = allowed_cohort

    # -- acreditación ----------------------------------------------------

    def active_accreditation(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        capability: AccreditationCapability,
        cutoff: str,
    ) -> str | None:
        row = connection.execute(
            "SELECT accreditation_id FROM professional_accreditations"
            " WHERE tenant_id = :tenant_id AND actor_id = :actor_id"
            f" AND {_ACTIVE_WINDOW}"
            " AND EXISTS (SELECT 1 FROM json_each(professional_accreditations.capabilities)"
            "             WHERE json_each.value = :capability)"
            " AND NOT EXISTS (SELECT 1 FROM professional_accreditations AS newer"
            "                 WHERE newer.supersedes_id ="
            "                       professional_accreditations.accreditation_id"
            "                   AND newer.ingested_at <= :cutoff)"
            " ORDER BY valid_from DESC LIMIT 1",
            {
                "tenant_id": actor.tenant_id,
                "actor_id": actor.actor_id,
                "capability": capability.value,
                "cutoff": cutoff,
            },
        ).fetchone()
        return None if row is None else row["accreditation_id"]

    # -- consentimiento --------------------------------------------------

    def active_consents(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        subject_id: str,
        purpose: ConsentPurpose,
        cutoff: str,
    ) -> tuple[str, ...]:
        rows = connection.execute(
            "SELECT consent_id FROM consents"
            " WHERE tenant_id = :tenant_id AND subject_id = :subject_id"
            " AND purpose = :purpose"
            f" AND {_ACTIVE_WINDOW}"
            " AND NOT EXISTS (SELECT 1 FROM consents AS newer"
            "                 WHERE newer.supersedes_id = consents.consent_id"
            "                   AND newer.ingested_at <= :cutoff)"
            " ORDER BY consent_id",
            {
                "tenant_id": tenant_id,
                "subject_id": subject_id,
                "purpose": purpose.value,
                "cutoff": cutoff,
            },
        ).fetchall()
        return tuple(row["consent_id"] for row in rows)

    # -- grants ----------------------------------------------------------

    def granted_subject_ids(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        capability: GrantCapability,
        cutoff: str,
    ) -> tuple[str, ...]:
        rows = connection.execute(
            GRANT_FILTER_SQL + " ORDER BY subject_id",
            {
                "tenant_id": actor.tenant_id,
                "actor_id": actor.actor_id,
                "capability": capability.value,
                "cutoff": cutoff,
            },
        ).fetchall()
        return tuple(row["subject_id"] for row in rows)

    def _grant(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        subject_id: str,
        capability: GrantCapability,
        cutoff: str,
    ) -> str | None:
        row = connection.execute(
            "SELECT subject_access_grant_id FROM subject_access_grants"
            " WHERE tenant_id = :tenant_id AND actor_id = :actor_id"
            " AND subject_id = :subject_id"
            f" AND {_ACTIVE_WINDOW}"
            " AND EXISTS (SELECT 1 FROM json_each(subject_access_grants.capabilities)"
            "             WHERE json_each.value = :capability)"
            " AND NOT EXISTS (SELECT 1 FROM subject_access_grants AS newer"
            "                 WHERE newer.supersedes_id ="
            "                       subject_access_grants.subject_access_grant_id"
            "                   AND newer.ingested_at <= :cutoff)"
            " ORDER BY valid_from DESC LIMIT 1",
            {
                "tenant_id": actor.tenant_id,
                "actor_id": actor.actor_id,
                "subject_id": subject_id,
                "capability": capability.value,
                "cutoff": cutoff,
            },
        ).fetchone()
        return None if row is None else row["subject_access_grant_id"]

    # -- comprobación completa -------------------------------------------

    def authorize_subject(
        self,
        connection: sqlite3.Connection,
        *,
        actor: ActorContext,
        subject_id: str,
        capability: GrantCapability,
        cutoff: str,
        allowed_roles: tuple[Role, ...] = (Role.CAREGIVER, Role.PROFESSIONAL),
        action: str = "subject_access",
    ) -> SubjectAuthorization:
        """Tenant, cohorte, rol, acreditación, capability y grant, en ese orden.

        Cross-tenant y same-tenant/wrong-subject responden 403 y quedan auditados
        (SPEC 13.2 / INV-31). No se distingue "no existe" de "no autorizado":
        ambos casos devuelven el mismo 403 para no filtrar la existencia de un
        sujeto de otra organización.
        """
        subject = connection.execute(
            "SELECT subject_id, tenant_id, cohort_kind, display_label FROM subjects"
            " WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()

        def deny(code: str) -> None:
            raise forbidden(
                code,
                audit=AuditIntent(
                    action=action,
                    resource_type="subject",
                    decision="denied",
                    reason_code=code,
                    tenant_id=actor.tenant_id,
                    actor_id=actor.actor_id,
                    resource_id=subject_id,
                    subject_id=subject_id,
                    request_id=actor.request_id,
                ),
                subject_id=subject_id,
                capability=capability.value,
            )

        if subject is None or subject["tenant_id"] != actor.tenant_id:
            deny("cross_tenant")
        assert subject is not None

        # SPEC 12.3: modo demo solo opera cohorte `demo_fixture`.
        if subject["cohort_kind"] != self._allowed_cohort.value:
            deny("cohort_not_allowed")

        if not actor.has_any_role(*allowed_roles):
            deny("role_not_allowed")

        accreditation_id: str | None = None
        if actor.has_role(Role.PROFESSIONAL) and not actor.has_role(Role.CAREGIVER):
            # SPEC 13.2: un professional exige acreditación organizacional vigente.
            accreditation_id = self.active_accreditation(
                connection,
                actor=actor,
                capability=AccreditationCapability.SUBJECT_CARE,
                cutoff=cutoff,
            )
            if accreditation_id is None:
                deny("accreditation_required")

        grant_id = self._grant(
            connection,
            actor=actor,
            subject_id=subject_id,
            capability=capability,
            cutoff=cutoff,
        )
        if grant_id is None:
            deny("subject_access_denied")
        assert grant_id is not None

        audit.record(
            connection,
            actor=actor,
            action=action,
            resource_type="subject",
            resource_id=subject_id,
            subject_id=subject_id,
            decision="allowed",
            reason_code=capability.value,
            occurred_at=cutoff,
            request_id=actor.request_id,
        )
        return SubjectAuthorization(
            subject_id=subject["subject_id"],
            tenant_id=subject["tenant_id"],
            cohort_kind=subject["cohort_kind"],
            display_label=subject["display_label"],
            grant_id=grant_id,
            capability=capability.value,
            accreditation_id=accreditation_id,
        )

    def require_tenant_resource(
        self,
        row: sqlite3.Row | None,
        *,
        actor: ActorContext,
        code: str = "not_found",
    ) -> sqlite3.Row:
        """Un recurso de otro tenant se comporta como inexistente."""
        if row is None or row["tenant_id"] != actor.tenant_id:
            raise not_found(code)
        return row
