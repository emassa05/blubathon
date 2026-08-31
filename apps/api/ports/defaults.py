"""Puerto de smart defaults y auditoría (P1.3 `ml/defaults`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AuditAssignment:
    """Se persiste al abrir la sesión y no se recalcula jamás."""

    audit_mode: bool
    bucket: int
    policy_version: str


@dataclass(frozen=True, slots=True)
class DefaultDecision:
    """Una sugerencia presentable, ya filtrada por umbral y allowlist.

    Si P1 decide no sugerir, el puerto devuelve `None`: nunca un valor con
    `lower_bound` bajo el corte ni un empate resuelto por conveniencia.
    """

    field_code: str
    value: Any
    candidate_count: int
    posterior_mean: float
    lower_bound: float
    n_observations: int
    estimator_version: str


class DefaultsPort(Protocol):
    def assign_audit_mode(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        local_date: date,
        policy_version: str,
    ) -> AuditAssignment: ...

    def default_for_field(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        source: str,
        field_code: str,
        as_of_at: str,
        audit_mode: bool,
    ) -> DefaultDecision | None: ...
