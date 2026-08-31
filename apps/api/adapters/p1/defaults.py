"""`ml.defaults` detrás del puerto de smart defaults.

P1 publica funciones puras sobre filas ya cargadas: el adaptador carga la
ventana desde el store, la convierte a `FieldObservation` y llama a
`eligible_history` y `compute_default_decision`. No decide nada por su cuenta:
el umbral, la allowlist, el empate y la auditoría son de P1.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from apps.api.adapters.p1 import rows as translate
from apps.api.canonical import parse_timestamp
from apps.api.ports.defaults import AuditAssignment, DefaultDecision
from apps.api.store import history
from apps.api.store.db import Database
from ml.defaults import assign_audit_mode, compute_default_decision, eligible_history
from ml.defaults.window import Stratum
from packages.shared.constants import DEFAULT_WINDOW_DAYS
from packages.shared.enums import FieldCode, Source


class P1Defaults:
    def __init__(self, *, database: Database, secret: bytes) -> None:
        self._database = database
        self._secret = secret

    def assign_audit_mode(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        local_date: date,
        policy_version: str,
    ) -> AuditAssignment:
        assignment = assign_audit_mode(
            secret=self._secret,
            tenant_id=UUID(tenant_id),
            subject_id=UUID(subject_id),
            local_date=local_date,
            policy_version=policy_version,
        )
        return AuditAssignment(
            audit_mode=assignment.audit_mode,
            bucket=assignment.bucket,
            policy_version=policy_version,
        )

    def default_for_field(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        field_code: str,
        as_of_at: str,
        audit_mode: bool,
    ) -> DefaultDecision | None:
        cutoff = parse_timestamp(as_of_at)
        connection = self._database.connection
        since = (cutoff.date() - timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat()
        observations = [
            translate.field_observation(row)
            for row in history.observations_for_subject(
                connection, tenant_id=tenant_id, subject_id=subject_id, since_local_date=since
            )
        ]
        approved = frozenset(
            UUID(item) for item in history.approved_mapping_ids(connection, tenant_id=tenant_id)
        )
        window = eligible_history(
            observations,
            stratum=Stratum(
                tenant_id=UUID(tenant_id),
                subject_id=UUID(subject_id),
                source=Source(source),
                field_code=FieldCode(field_code),
            ),
            cutoff=cutoff,
            approved_mapping_ids=approved,
        )
        decision = compute_default_decision(window, audit_mode=audit_mode)
        posterior = decision.to_contract()
        if posterior is None:
            return None
        return DefaultDecision(
            field_code=str(posterior.field_code),
            value=posterior.candidate_value,
            candidate_count=posterior.candidate_count,
            posterior_mean=posterior.posterior_mean,
            lower_bound=posterior.lower_bound,
            n_observations=posterior.n_observations,
            estimator_version=posterior.estimator_version,
        )
