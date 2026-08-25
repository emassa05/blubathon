"""Traducción de filas SQLite a los modelos publicados en `packages/shared`.

Aquí vive el trabajo que el encargo pone en el adaptador: el store devuelve
filas, el dominio de P1 recibe modelos del contrato, y nadie en medio reescribe
su firma. Ninguna función de este módulo calcula: convierte tipos y falla si una
fila no cumple el contrato, en vez de rellenar un campo ausente.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any
from uuid import UUID

from apps.api.canonical import parse_timestamp
from apps.api.store.json_columns import load, load_list
from packages.shared.domain.identity import SubjectProfile
from packages.shared.domain.observation import FieldObservation, FormSession, QuestionPresentation
from packages.shared.domain.outcome import OutcomeResolution
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.domain.rag import (
    CatalogVersion,
    RecommendationSetVersion,
    ScenarioPredicate,
    StrategyCitation,
    StrategyVersion,
)
from packages.shared.enums import VoiStatus


def instant(value: str) -> datetime:
    return parse_timestamp(value)


def optional_instant(value: str | None) -> datetime | None:
    return None if value is None else parse_timestamp(value)


def local_day(value: str) -> date:
    return date.fromisoformat(value)


def identifier(value: str | None) -> UUID | None:
    return None if value is None else UUID(str(value))


def field_observation(row: sqlite3.Row) -> FieldObservation:
    return FieldObservation(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        field_observation_id=UUID(row["field_observation_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=identifier(row["form_session_id"]),
        field_code=row["field_code"],
        value=load(row["value"]),
        source=row["source"],
        actor_id=UUID(row["actor_id"]),
        entry_mode=row["entry_mode"],
        data_origin=row["data_origin"],
        cohort_kind=row["cohort_kind"],
        effective_at=instant(row["effective_at"]),
        local_date=local_day(row["local_date"]),
        source_mapping_id=identifier(row["source_mapping_id"]),
    )


def form_session(row: sqlite3.Row) -> FormSession:
    return FormSession(
        form_session_id=UUID(row["form_session_id"]),
        tenant_id=UUID(row["tenant_id"]),
        subject_id=UUID(row["subject_id"]),
        actor_id=UUID(row["actor_id"]),
        source=row["source"],
        session_kind=row["session_kind"],
        status=row["status"],
        audit_mode=bool(row["audit_mode"]),
        form_policy_version=row["form_policy_version"],
        opened_at=instant(row["opened_at"]),
        submitted_at=optional_instant(row["submitted_at"]),
        prediction_episode_id=identifier(row["prediction_episode_id"]),
        linked_prediction_episode_id=identifier(row["linked_prediction_episode_id"]),
    )


def question_presentation(row: sqlite3.Row) -> QuestionPresentation:
    return QuestionPresentation(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["presented_at"]),
        question_presentation_id=UUID(row["question_presentation_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=UUID(row["form_session_id"]),
        field_code=row["field_code"],
        source=row["source"],
        highlighted=bool(row["highlighted"]),
        reason=row["reason"],
        presented_at=instant(row["presented_at"]),
        local_date=local_day(row["local_date"]),
        voi_nats=row["voi_nats"],
        # P2 persiste el valor, no el estado: sin VoI la fila guarda `null`, que
        # es exactamente `unavailable_model` (SPEC 7.3 / INV-09).
        voi_status=(
            VoiStatus.UNAVAILABLE_MODEL if row["voi_nats"] is None else VoiStatus.AVAILABLE
        ),
    )


def subject_profile(row: sqlite3.Row) -> SubjectProfile:
    return SubjectProfile(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        subject_profile_id=UUID(row["subject_profile_id"]),
        subject_id=UUID(row["subject_id"]),
        sensory_profile_tags=frozenset(load_list(row["sensory_profile_tags"])),
        communication_support_tags=frozenset(load_list(row["communication_support_tags"])),
        contraindication_tags=frozenset(load_list(row["contraindication_tags"])),
        care_mode=row["care_mode"],
        profile_version=row["profile_version"],
        effective_from=instant(row["effective_from"]),
        recorded_at=instant(row["recorded_at"]),
    )


def prediction_episode(row: sqlite3.Row) -> PredictionEpisode:
    return PredictionEpisode(
        prediction_episode_id=UUID(row["prediction_episode_id"]),
        tenant_id=UUID(row["tenant_id"]),
        subject_id=UUID(row["subject_id"]),
        form_session_id=UUID(row["form_session_id"]),
        role=row["role"],
        status=row["status"],
        as_of_at=instant(row["as_of_at"]),
        prediction_at=instant(row["prediction_at"]),
        target_start_at=instant(row["target_start_at"]),
        target_end_at=instant(row["target_end_at"]),
        capture_deadline_at=instant(row["capture_deadline_at"]),
        target_definition_version=row["target_definition_version"],
        care_mode=row["care_mode"],
        profile_version=row["profile_version"],
        cohort_kind=row["cohort_kind"],
        input_data_origin=row["input_data_origin"],
        feature_snapshot_id=identifier(row["feature_snapshot_id"]),
        created_at=instant(row["created_at"]),
    )


def outcome_resolution(row: sqlite3.Row) -> OutcomeResolution:
    return OutcomeResolution(
        tenant_id=UUID(row["tenant_id"]),
        ingested_at=instant(row["ingested_at"]),
        supersedes_id=identifier(row["supersedes_id"]),
        outcome_resolution_id=UUID(row["outcome_resolution_id"]),
        prediction_episode_id=UUID(row["prediction_episode_id"]),
        status=row["status"],
        resolved_at=optional_instant(row["resolved_at"]),
        qualifying_report_id=identifier(row["qualifying_report_id"]),
        ever_conflicted=bool(row["ever_conflicted"]),
        resolution_version=int(row["resolution_version"]),
    )


def scenario_predicate(raw: str | dict[str, Any] | None) -> ScenarioPredicate:
    payload = raw if isinstance(raw, dict) else load(raw, {})
    return ScenarioPredicate.model_validate(payload or {})


def strategy_citation(row: sqlite3.Row) -> StrategyCitation:
    return StrategyCitation(
        citation_id=UUID(row["citation_id"]),
        claim_id=UUID(row["claim_id"]),
        document_chunk_id=UUID(row["document_chunk_id"]),
        locator=row["locator"],
        quoted_text=row["quoted_text"],
        # `StrategyCitation` verifica el chunk citado, no el texto citado: el
        # hash sale de `document_chunks`, no de `strategy_citations`.
        chunk_sha256=row["chunk_sha256"],
        canonical_url=row["canonical_url"],
    )


def strategy_version(row: sqlite3.Row, citations: tuple[StrategyCitation, ...]) -> StrategyVersion:
    return StrategyVersion(
        strategy_id=UUID(row["strategy_id"]),
        strategy_version_id=UUID(row["strategy_version_id"]),
        purpose_es=row["purpose_es"],
        action_text_es=row["action_text_es"],
        claims=tuple(load_list(row["claims"])),
        citations=citations,
        applicability_predicate=scenario_predicate(row["applicability_predicate"]),
        required_approver_role=row["required_approver_role"],
        allowed_executor_roles=frozenset(load_list(row["allowed_executor_roles"])),
        corpus_version=row["corpus_version"],
        evidence_review_id=identifier(row["evidence_review_id"]),
        clinical_review_id=identifier(row["clinical_review_id"]),
        effective_from=instant(row["effective_from"]),
        supersedes_version_id=identifier(row["supersedes_version_id"]),
        status=row["status"],
        content_sha256=row["content_sha256"],
    )


def recommendation_set_version(row: sqlite3.Row) -> RecommendationSetVersion:
    # `RuntimeCatalog` compara `CatalogVersion.recommendation_set_version_ids`
    # contra `RecommendationSetVersion.recommendation_set_id`: la identidad de un
    # set dentro de un catálogo es la de su versión, que es lo que P2 persiste.
    return RecommendationSetVersion(
        recommendation_set_id=UUID(row["recommendation_set_version_id"]),
        recommendation_set_version=row["recommendation_set_version"],
        applicability_predicate=scenario_predicate(row["applicability_predicate"]),
        ordered_strategy_version_ids=tuple(
            UUID(str(item)) for item in load_list(row["ordered_strategy_version_ids"])
        ),
        reviewed_priority=int(row["reviewed_priority"]),
        clinical_review_id=identifier(row["clinical_review_id"]),
        status=row["status"],
        effective_from=instant(row["effective_from"]),
        suspended_at=optional_instant(row["suspended_at"]),
        content_sha256=row["content_sha256"],
    )


def catalog_version(row: sqlite3.Row) -> CatalogVersion:
    return CatalogVersion(
        catalog_version=row["catalog_version"],
        tenant_id=UUID(row["tenant_id"]),
        corpus_version=row["corpus_version"],
        recommendation_set_version_ids=tuple(
            UUID(str(item)) for item in load_list(row["recommendation_set_version_ids"])
        ),
        catalog_activation_review_id=identifier(row["catalog_activation_review_id"]),
        status=row["status"],
        effective_from=instant(row["effective_from"]),
        suspended_at=optional_instant(row["suspended_at"]),
        content_sha256=row["content_sha256"],
    )
