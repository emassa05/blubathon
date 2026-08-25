"""`build_scenario`: the pure P1 facade for the minimal matching payload (SPEC 9.7).

P2 calls this and persists the result or the abstention. It does not
reimplement the precedence, because the interesting part of this function is
what it refuses to include: no identity, no notes, no external IDs, no outcomes,
no history, and nothing dated after the cutoff.

The payload is treated as potentially pseudonymised, never presumed anonymous: a
combination of tags can still be linkable. Its hash is keyed with a tenant
secret because the space of scenarios is small enough to enumerate.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from packages.shared.canonical import keyed_hash
from packages.shared.constants import (
    SCENARIO_BUILDER_VERSION,
    SCENARIO_SCHEMA_VERSION,
)
from packages.shared.domain.identity import SubjectProfile
from packages.shared.domain.observation import FieldObservation, FormSession
from packages.shared.domain.rag import ScenarioBuildResult, ScenarioV1
from packages.shared.enums import (
    FieldCode,
    FormSessionStatus,
    RecommendationAbstentionReason,
    RuntimeStatus,
)
from packages.shared.field_catalog import SCENARIO_ALLOWLIST_V1, TAG_PATTERN
from packages.shared.projection import project_as_of, unique_active

SCENARIO_HASH_ARTIFACT = "scenario"


@dataclass(frozen=True, slots=True)
class ScenarioInputs:
    """Everything `build_scenario` may look at, and nothing else."""

    form_session: FormSession
    as_of_at: datetime
    observations: Iterable[FieldObservation]
    profile: SubjectProfile
    context_tags: frozenset[str] = frozenset()
    tenant_secret: bytes = b""


def _abstain(reason: RecommendationAbstentionReason) -> ScenarioBuildResult:
    return ScenarioBuildResult(
        status=RuntimeStatus.ABSTAINED,
        builder_version=SCENARIO_BUILDER_VERSION,
        reasons=(reason,),
    )


def build_scenario(
    inputs: ScenarioInputs,
    *,
    submitted_form_session_id: UUID,
    scenario_schema_version: str = SCENARIO_SCHEMA_VERSION,
) -> ScenarioBuildResult:
    """Build `ScenarioV1` from one submitted session, fail-closed at every step."""

    session = inputs.form_session
    if scenario_schema_version != SCENARIO_SCHEMA_VERSION:
        raise ValueError(f"unknown scenario schema {scenario_schema_version!r}")
    if session.form_session_id != submitted_form_session_id:
        raise ValueError("the session does not match the submitted session id")
    if session.status is not FormSessionStatus.SUBMITTED or session.submitted_at is None:
        raise ValueError("a scenario is built from a submitted session")
    if session.submitted_at != inputs.as_of_at:
        raise ValueError("the snapshot cutoff is the session submitted_at")
    if not inputs.profile.profile_version:
        raise ValueError("the episode must have captured a profile version")

    projection = project_as_of(inputs.observations, inputs.as_of_at)
    session_rows = [
        row
        for row in projection.leaves
        if row.form_session_id == session.form_session_id
        and row.tenant_id == session.tenant_id
        and row.subject_id == session.subject_id
        and row.field_code in SCENARIO_ALLOWLIST_V1
    ]
    grouped = unique_active(
        project_as_of(session_rows, inputs.as_of_at), key=lambda row: row.field_code
    )
    if not grouped.is_clean:
        return _abstain(RecommendationAbstentionReason.SCENARIO_UNAVAILABLE_CONFLICT)

    field_values: dict[FieldCode, str] = {}
    for field_code, row in grouped.rows.items():
        if row.value is None:
            # Missing and explicit unknown are simply omitted; neither is a value.
            continue
        if not isinstance(row.value, str):
            raise ValueError(f"{field_code} is not a categorical scenario field")
        field_values[field_code] = row.value

    context_tags = {str(session.source)}
    for tag in inputs.context_tags:
        if not TAG_PATTERN.match(tag):
            raise ValueError(f"{tag!r} is not a closed context tag")
        context_tags.add(tag)

    scenario = ScenarioV1(
        schema_version=scenario_schema_version,
        field_values=field_values,
        context_tags=tuple(sorted(context_tags)),
        profile_tags=inputs.profile.namespaced_profile_tags(),
        contraindication_tags=tuple(sorted(inputs.profile.contraindication_tags)),
    )

    if not inputs.tenant_secret:
        raise ValueError("a scenario hash needs the tenant secret")
    scenario_hash = keyed_hash(
        inputs.tenant_secret,
        SCENARIO_HASH_ARTIFACT,
        scenario_schema_version,
        scenario.canonical_payload(),
    )

    return ScenarioBuildResult(
        status=RuntimeStatus.MATCHED,
        scenario=scenario,
        scenario_hash=scenario_hash,
        builder_version=SCENARIO_BUILDER_VERSION,
        source=session.source,
        profile_version=inputs.profile.profile_version,
    )
