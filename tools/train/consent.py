"""Consent re-authorisation at the start of every run (SPEC 13.2, TAREAS P1.8).

A snapshot records the consents it used, but that is not enough. Every training
and evaluation run re-checks `secondary_model_use` for every subject in the
snapshot, at the moment the run starts, because a person may have revoked since.

What a revocation does is deliberately asymmetric: the snapshot stays immutable
for audit, a new run over it is blocked, and dependent real artifacts are
suspended for consent review. Synthetic artifacts are untouched, because no
person's data is in them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from packages.shared.domain.evaluation import EvaluationReport, ModelVersion
from packages.shared.domain.identity import Consent, ConsentRevocationImpact
from packages.shared.enums import (
    ConsentPurpose,
    DataOrigin,
    EvaluationReportStatus,
    ModelState,
)
from packages.shared.projection import project_as_of

TERMINAL_MODEL_STATES: frozenset[ModelState] = frozenset(
    {ModelState.REJECTED, ModelState.RETIRED, ModelState.SUSPENDED_FOR_CONSENT_REVIEW}
)


@dataclass(frozen=True, slots=True)
class ConsentAuthorization:
    """The answer to: may this run read these subjects, right now?"""

    authorized: bool
    consent_ids: tuple[UUID, ...] = ()
    unauthorized_subject_ids: tuple[UUID, ...] = ()

    @property
    def blocks_the_run(self) -> bool:
        return not self.authorized


def authorize_secondary_model_use(
    consents: Iterable[Consent],
    *,
    subject_ids: Iterable[UUID],
    at: datetime,
    purpose: ConsentPurpose = ConsentPurpose.SECONDARY_MODEL_USE,
) -> ConsentAuthorization:
    """Re-authorise every subject at `at`, reading the projected active leaf.

    A purpose is never substituted for another: an operational consent does not
    authorise model training (SPEC 13.1).
    """

    projection = project_as_of(tuple(consents), at)
    granted: dict[UUID, UUID] = {}
    for consent in projection.leaves:
        if consent.covers(purpose, at):
            granted.setdefault(consent.subject_id, consent.consent_id)

    wanted = tuple(dict.fromkeys(subject_ids))
    missing = tuple(subject_id for subject_id in wanted if subject_id not in granted)
    used = sorted((granted[subject] for subject in wanted if subject in granted), key=str)
    return ConsentAuthorization(
        authorized=bool(wanted) and not missing,
        consent_ids=tuple(used),
        unauthorized_subject_ids=missing,
    )


def revocation_impact(
    *,
    subject_id: UUID,
    revoked_at: datetime,
    purpose: ConsentPurpose = ConsentPurpose.SECONDARY_MODEL_USE,
) -> ConsentRevocationImpact:
    """What a revocation changes, stated once so nobody has to infer it."""

    return ConsentRevocationImpact(
        subject_id=subject_id,
        revoked_at=revoked_at,
        purpose=purpose,
        blocks_new_runs=True,
        keeps_existing_snapshots_immutable=True,
        suspends_dependent_real_artifacts=True,
        affects_synthetic_artifacts=False,
    )


def suspend_dependent_models(
    models: Iterable[ModelVersion], *, at: datetime
) -> tuple[ModelVersion, ...]:
    """Real, non-terminal model versions move to `suspended_for_consent_review`."""

    suspended: list[ModelVersion] = []
    for model in models:
        if model.training_data_origin is not DataOrigin.REAL:
            continue
        if model.state in TERMINAL_MODEL_STATES:
            continue
        suspended.append(
            ModelVersion(
                model_version=model.model_version,
                track_id=model.track_id,
                training_run_id=model.training_run_id,
                training_data_origin=model.training_data_origin,
                intended_use=model.intended_use,
                state=ModelState.SUSPENDED_FOR_CONSENT_REVIEW,
                artifact_sha256=model.artifact_sha256,
                created_at=model.created_at,
                suspended_at=at,
            )
        )
    return tuple(suspended)


def suspend_dependent_reports(
    reports: Iterable[EvaluationReport], *, at: datetime
) -> tuple[EvaluationReport, ...]:
    """Real published reports are suspended for review; synthetic ones are not."""

    suspended: list[EvaluationReport] = []
    for report in reports:
        if report.data_origin is not DataOrigin.REAL:
            continue
        if report.status in {
            EvaluationReportStatus.SUSPENDED_FOR_CONSENT_REVIEW,
            EvaluationReportStatus.RETIRED,
        }:
            continue
        suspended.append(
            report.model_copy(
                update={
                    "status": EvaluationReportStatus.SUSPENDED_FOR_CONSENT_REVIEW,
                    "detail": {**report.detail, "suspended_at": at.isoformat()},
                }
            )
        )
    return tuple(suspended)
