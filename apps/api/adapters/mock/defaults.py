"""Defaults y auditoría fixture (sustituye `ml/defaults` hasta H1).

`assign_audit_mode` sí implementa la asignación HMAC del SPEC 6.8 porque es una
regla determinista de asignación, no un estimador: P2 necesita persistirla al
abrir la sesión para que INV-05 sea comprobable. Queda marcada como duplicación
temporal y desaparece cuando P1 publique `ml.defaults.assign_audit_mode`.

`default_for_field` **no** estima nada: lee sugerencias declaradas en un fixture.
Un campo sin entrada no recibe sugerencia, que es el comportamiento seguro.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date
from pathlib import Path
from typing import Any

from apps.api.contracts.constants import (
    DEFAULT_LOWER_THRESHOLD,
    DEFAULTS_ESTIMATOR_VERSION,
)
from apps.api.contracts.field_catalog import DEFAULT_ALLOWLIST_V1
from apps.api.ports.defaults import AuditAssignment, DefaultDecision

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUDIT_BUCKETS = 1000
AUDIT_BUCKET_CUTOFF = 100  # 10% de SPEC 6.8 / C10 expresado en milésimas.


class MockDefaults:
    def __init__(self, *, secret: bytes = b"blubathon-demo-audit-secret") -> None:
        self._secret = secret
        self._suggestions: dict[str, dict[str, Any]] = json.loads(
            (FIXTURES / "defaults.json").read_text(encoding="utf-8")
        )

    def assign_audit_mode(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        local_date: date,
        policy_version: str,
    ) -> AuditAssignment:
        message = "|".join((tenant_id, subject_id, local_date.isoformat(), policy_version))
        digest = hmac.new(self._secret, message.encode("utf-8"), hashlib.sha256).digest()
        bucket = int.from_bytes(digest, "big") % AUDIT_BUCKETS
        return AuditAssignment(
            audit_mode=bucket < AUDIT_BUCKET_CUTOFF,
            bucket=bucket,
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
        # SPEC 6.6: una sesión auditada nunca devuelve sugerencias.
        if audit_mode or field_code not in DEFAULT_ALLOWLIST_V1:
            return None
        entry = self._suggestions.get(f"{subject_id}|{source}|{field_code}")
        if entry is None:
            return None
        # SPEC 6.6: el corte es estricto. Un fixture bajo el umbral no se muestra.
        if float(entry["lower_bound"]) <= DEFAULT_LOWER_THRESHOLD:
            return None
        return DefaultDecision(
            field_code=field_code,
            value=entry["value"],
            candidate_count=int(entry["candidate_count"]),
            posterior_mean=float(entry["posterior_mean"]),
            lower_bound=float(entry["lower_bound"]),
            n_observations=int(entry["n_observations"]),
            estimator_version=str(entry.get("estimator_version", DEFAULTS_ESTIMATOR_VERSION)),
        )
