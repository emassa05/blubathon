"""Comandos de siembra (M0 P2.5, P2.4)."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from apps.api.canonical import canonical_timestamp, content_hash
from apps.api.contracts.constants import SPEC_VERSION
from apps.api.store.json_columns import dump
from tools.seed import data, ids

CatalogProfile = Literal["blocked", "fixture-active"]

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
POLICY_VERSION = "demo-accreditation-policy-0.3.0"


def _id(*parts: str) -> str:
    """UUID v4 determinista a partir de un nombre estable."""
    raw = uuid5(NAMESPACE_URL, "blubathon-seed:" + "|".join(parts)).hex
    return f"{raw[:8]}-{raw[8:12]}-4{raw[13:16]}-8{raw[17:20]}-{raw[20:32]}"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SeedResult:
    catalog_profile: CatalogProfile
    catalog_version: str | None
    strategy_version_ids: tuple[str, ...]
    tokens: dict[str, str]


def seed(
    connection: sqlite3.Connection,
    *,
    catalog_profile: CatalogProfile = "blocked",
    now: datetime | None = None,
) -> SeedResult:
    moment = canonical_timestamp(now or EPOCH)
    valid_from = canonical_timestamp((now or EPOCH) - timedelta(days=1))

    _seed_identity(connection, moment=moment, valid_from=valid_from)
    _seed_target(connection, moment=moment)
    _seed_corpus(connection, moment=moment)
    strategy_ids = _seed_strategies(
        connection, moment=moment, activate=catalog_profile == "fixture-active"
    )
    catalog_version = None
    if catalog_profile == "fixture-active":
        catalog_version = _seed_catalog(
            connection, moment=moment, strategy_version_ids=strategy_ids
        )
    return SeedResult(
        catalog_profile=catalog_profile,
        catalog_version=catalog_version,
        strategy_version_ids=strategy_ids,
        tokens=dict(ids.TOKENS),
    )


def _seed_identity(connection: sqlite3.Connection, *, moment: str, valid_from: str) -> None:
    for tenant in data.TENANTS:
        connection.execute(
            "INSERT OR IGNORE INTO tenants(tenant_id, name, deployment_mode, created_at)"
            " VALUES (?, ?, 'demo', ?)",
            (tenant["tenant_id"], tenant["name"], moment),
        )
    for user in data.USERS:
        connection.execute(
            "INSERT OR IGNORE INTO users(user_id, tenant_id, display_name,"
            " demo_session_token, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                user["user_id"],
                user["tenant_id"],
                user["display_name"],
                ids.TOKENS[user["user_id"]],
                moment,
            ),
        )
        for role in user["roles"]:
            connection.execute(
                "INSERT OR IGNORE INTO user_roles(user_role_id, tenant_id, user_id, role,"
                " granted_at) VALUES (?, ?, ?, ?, ?)",
                (
                    _id("role", user["user_id"], role),
                    user["tenant_id"],
                    user["user_id"],
                    role,
                    moment,
                ),
            )

    # Acreditaciones profesionales: la demo declara su política y su emisor.
    for actor_id, tenant_id, capabilities in (
        (ids.PROFESSIONAL_A, ids.TENANT_A, ("subject_care",)),
        (ids.PROFESSIONAL_B, ids.TENANT_B, ("subject_care",)),
        (ids.MODEL_EVALUATOR_A, ids.TENANT_A, ("model_evaluation",)),
    ):
        issuer = ids.TENANT_ADMIN_A if tenant_id == ids.TENANT_A else ids.TENANT_ADMIN_B
        connection.execute(
            "INSERT OR IGNORE INTO professional_accreditations(accreditation_id, tenant_id,"
            " actor_id, capabilities, credential_policy_version, issuer_actor_id,"
            " valid_from, valid_until, revoked_at, status, supersedes_id, ingested_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'active', NULL, ?)",
            (
                _id("accreditation", actor_id),
                tenant_id,
                actor_id,
                dump(sorted(capabilities)),
                POLICY_VERSION,
                issuer,
                valid_from,
                moment,
            ),
        )

    for subject in data.SUBJECTS:
        connection.execute(
            "INSERT OR IGNORE INTO subjects(subject_id, tenant_id, display_label,"
            " cohort_kind, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                subject["subject_id"],
                subject["tenant_id"],
                subject["display_label"],
                subject["cohort_kind"],
                moment,
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO subject_profiles(subject_profile_id, tenant_id, subject_id,"
            " sensory_profile_tags, communication_support_tags, contraindication_tags,"
            " care_mode, profile_version, effective_from, recorded_at, supersedes_id,"
            " ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
            (
                _id("profile", subject["subject_id"]),
                subject["tenant_id"],
                subject["subject_id"],
                dump(subject["sensory_profile_tags"]),
                dump(subject["communication_support_tags"]),
                dump(subject["contraindication_tags"]),
                subject["care_mode"],
                "profile-1",
                valid_from,
                moment,
                moment,
            ),
        )

    for actor_id, subject_id, capabilities in data.GRANTS:
        tenant_id = next(
            item["tenant_id"] for item in data.SUBJECTS if item["subject_id"] == subject_id
        )
        issuer = ids.TENANT_ADMIN_A if tenant_id == ids.TENANT_A else ids.TENANT_ADMIN_B
        connection.execute(
            "INSERT OR IGNORE INTO subject_access_grants(subject_access_grant_id, tenant_id,"
            " subject_id, actor_id, capabilities, issuer_actor_id, valid_from, valid_until,"
            " revoked_at, status, supersedes_id, ingested_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'active', NULL, ?)",
            (
                _id("grant", actor_id, subject_id),
                tenant_id,
                subject_id,
                actor_id,
                dump(sorted(capabilities)),
                issuer,
                valid_from,
                moment,
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO consents(consent_id, tenant_id, subject_id,"
            " grantor_actor_id, purpose, policy_version, granted_at, valid_from, valid_until,"
            " revoked_at, status, supersedes_id, ingested_at)"
            " VALUES (?, ?, ?, ?, 'operational_support', ?, ?, ?, NULL, NULL, 'active',"
            " NULL, ?)",
            (
                _id("consent", subject_id),
                tenant_id,
                subject_id,
                issuer,
                POLICY_VERSION,
                valid_from,
                valid_from,
                moment,
            ),
        )


def _seed_target(connection: sqlite3.Connection, *, moment: str) -> None:
    for target in (data.TARGET_DEMO, data.TARGET_TENANT_A):
        _insert_target(connection, target=target, moment=moment)


def _insert_target(connection: sqlite3.Connection, *, target: dict[str, Any], moment: str) -> None:
    payload = {key: target[key] for key in sorted(target)}
    connection.execute(
        "INSERT OR IGNORE INTO target_definition_versions(target_definition_version, scope,"
        " tenant_id, question_es, severity_anchors_es, eligible_reporter_roles,"
        " eligible_source_mappings, effective_from, retired_at, evidence_basis,"
        " approval_status, clinical_review_id, content_sha256, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 'active', NULL, ?, ?)",
        (
            target["target_definition_version"],
            target["scope"],
            target.get("tenant_id"),
            target["question_es"],
            dump(target["severity_anchors_es"]),
            dump(target["eligible_reporter_roles"]),
            dump(target["eligible_source_mappings"]),
            "2026-01-01T00:00:00.000Z",
            target["evidence_basis"],
            content_hash("target_definition_version", SPEC_VERSION, payload),
            moment,
        ),
    )


def _seed_corpus(connection: sqlite3.Connection, *, moment: str) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO corpus_versions(corpus_version, status, effective_from,"
        " suspended_at, retired_at, content_sha256, created_at)"
        " VALUES (?, 'active', ?, NULL, NULL, ?, ?)",
        (ids.CORPUS_FIXTURE, "2026-01-01T00:00:00.000Z", _sha(ids.CORPUS_FIXTURE), moment),
    )
    document = data.FIXTURE_DOCUMENT
    document_version_id = _id("document", document["source_id"], document["document_version"])
    connection.execute(
        "INSERT OR IGNORE INTO document_versions(document_version_id, source_id, publisher,"
        " title, document_version, publication_date, retrieved_at, canonical_url,"
        " rights_basis, original_bytes_sha256, extracted_text_sha256,"
        " extraction_manifest_id, language, status, corpus_version, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
        (
            document_version_id,
            document["source_id"],
            document["publisher"],
            document["title"],
            document["document_version"],
            document["publication_date"],
            moment,
            document["canonical_url"],
            document["rights_basis"],
            _sha("original:" + document["source_id"]),
            _sha("extracted:" + document["source_id"]),
            _id("manifest", document["source_id"]),
            document["language"],
            ids.CORPUS_FIXTURE,
            moment,
        ),
    )
    connection.execute(
        "INSERT OR IGNORE INTO authoring_build_manifests(authoring_build_manifest_id,"
        " corpus_version, retrieval_mode, payload, content_sha256, created_at)"
        " VALUES (?, ?, 'lexical_only', ?, ?, ?)",
        (
            _id("build", ids.CORPUS_FIXTURE),
            ids.CORPUS_FIXTURE,
            dump(
                {
                    "note_es": (
                        "Manifest ficticio de demostración. El build real y sus hashes "
                        "los produce tools/rag_authoring (P1)."
                    ),
                    "retrieval_mode": "lexical_only",
                }
            ),
            _sha("build:" + ids.CORPUS_FIXTURE),
            moment,
        ),
    )
    for index, chunk in enumerate(data.FIXTURE_CHUNKS):
        connection.execute(
            "INSERT OR IGNORE INTO document_chunks(document_chunk_id, document_version_id,"
            " locator, text, chunk_sha256, chunker_version, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'chunker-fixture-1', ?)",
            (
                _id("chunk", document["source_id"], str(index)),
                document_version_id,
                chunk["locator"],
                chunk["text"],
                _sha(chunk["text"]),
                moment,
            ),
        )


def _seed_strategies(
    connection: sqlite3.Connection, *, moment: str, activate: bool
) -> tuple[str, ...]:
    """Estrategias fixture.

    Sin revisor clínico autorizado quedan en `evidence_reviewed`: es el estado
    que se exige cuando el bloqueo clínico está activo.
    """
    document = data.FIXTURE_DOCUMENT
    created: list[str] = []
    for strategy in data.FIXTURE_STRATEGIES:
        strategy_id = _id("strategy", strategy["key"])
        strategy_version_id = _id("strategy-version", strategy["key"], "1")
        connection.execute(
            "INSERT OR IGNORE INTO strategies(strategy_id, created_at) VALUES (?, ?)",
            (strategy_id, moment),
        )
        evidence_review_id = _seed_authoring_review(
            connection,
            object_type="strategy",
            object_version_id=strategy_version_id,
            review_kind="evidence",
            actor_id=ids.TENANT_ADMIN_A,
            moment=moment,
            content=strategy["action_text_es"],
        )
        clinical_review_id = None
        if activate:
            clinical_review_id = _seed_authoring_review(
                connection,
                object_type="strategy",
                object_version_id=strategy_version_id,
                review_kind="clinical",
                actor_id=ids.PROFESSIONAL_A,
                moment=moment,
                content=strategy["action_text_es"],
            )

        if strategy["claim_text_es"] not in strategy["action_text_es"]:
            raise ValueError(f"claim no literal en la estrategia {strategy['key']}")
        chunk_text = data.FIXTURE_CHUNKS[strategy["chunk_index"]]["text"]
        if strategy["quoted_text"] not in chunk_text:
            raise ValueError(f"cita no literal en la estrategia {strategy['key']}")
        start = strategy["action_text_es"].index(strategy["claim_text_es"])
        claim_id = _id("claim", strategy["key"])
        claims = [
            {
                "claim_id": claim_id,
                "start": start,
                "end": start + len(strategy["claim_text_es"]),
                "claim_text_es": strategy["claim_text_es"],
                "citation_ids": [_id("citation", strategy["key"])],
            }
        ]
        payload = {
            "action_text_es": strategy["action_text_es"],
            "claims": claims,
            "applicability_predicate": strategy["predicate"],
        }
        connection.execute(
            "INSERT OR IGNORE INTO strategy_versions(strategy_version_id, strategy_id,"
            " purpose_es, action_text_es, claims, applicability_predicate,"
            " required_approver_role, allowed_executor_roles, corpus_version,"
            " evidence_review_id, clinical_review_id, effective_from, supersedes_version_id,"
            " status, suspended_at, content_sha256, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?, ?)",
            (
                strategy_version_id,
                strategy_id,
                strategy["purpose_es"],
                strategy["action_text_es"],
                dump(claims),
                dump(strategy["predicate"]),
                strategy["required_approver_role"],
                dump(strategy["allowed_executor_roles"]),
                ids.CORPUS_FIXTURE,
                evidence_review_id,
                clinical_review_id,
                "2026-01-01T00:00:00.000Z",
                "active" if activate else "evidence_reviewed",
                content_hash("strategy_version", SPEC_VERSION, payload),
                moment,
            ),
        )
        chunk_id = _id("chunk", document["source_id"], str(strategy["chunk_index"]))
        connection.execute(
            "INSERT OR IGNORE INTO strategy_citations(citation_id, strategy_version_id,"
            " claim_id, document_chunk_id, locator, quoted_text, quoted_text_sha256,"
            " canonical_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _id("citation", strategy["key"]),
                strategy_version_id,
                claim_id,
                chunk_id,
                data.FIXTURE_CHUNKS[strategy["chunk_index"]]["locator"],
                strategy["quoted_text"],
                _sha(strategy["quoted_text"]),
                document["canonical_url"],
                moment,
            ),
        )
        created.append(strategy_version_id)
    return tuple(created)


def _seed_authoring_review(
    connection: sqlite3.Connection,
    *,
    object_type: str,
    object_version_id: str,
    review_kind: str,
    actor_id: str,
    moment: str,
    content: str,
) -> str:
    """Review de autoría con actor acreditado, hash y decisión."""
    review_id = _id("authoring-review", object_version_id, review_kind)
    accreditation_id = _id("accreditation", actor_id)
    connection.execute(
        "INSERT OR IGNORE INTO professional_accreditations(accreditation_id, tenant_id,"
        " actor_id, capabilities, credential_policy_version, issuer_actor_id, valid_from,"
        " valid_until, revoked_at, status, supersedes_id, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'active', NULL, ?)",
        (
            accreditation_id,
            ids.TENANT_A,
            actor_id,
            dump(
                sorted(
                    {
                        "subject_care",
                        "evidence_review",
                        "strategy_review",
                        "catalog_activation",
                    }
                )
            ),
            POLICY_VERSION,
            ids.TENANT_ADMIN_A,
            "2025-12-31T00:00:00.000Z",
            moment,
        ),
    )
    connection.execute(
        "INSERT OR IGNORE INTO authoring_reviews(authoring_review_id, tenant_id, object_type,"
        " object_version_id, review_kind, actor_id, accreditation_id, decision,"
        " reviewed_content_sha256, reviewed_at, supersedes_id, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'approved', ?, ?, NULL, ?)",
        (
            review_id,
            ids.TENANT_A,
            object_type,
            object_version_id,
            review_kind,
            actor_id,
            accreditation_id,
            _sha(content),
            moment,
            moment,
        ),
    )
    return review_id


def _seed_catalog(
    connection: sqlite3.Connection, *, moment: str, strategy_version_ids: tuple[str, ...]
) -> str:
    set_id = _id("recommendation-set", "fixture")
    set_version_id = _id("recommendation-set-version", "fixture", "1")
    connection.execute(
        "INSERT OR IGNORE INTO recommendation_sets(recommendation_set_id, tenant_id,"
        " created_at) VALUES (?, ?, ?)",
        (set_id, ids.TENANT_A, moment),
    )
    set_review_id = _seed_authoring_review(
        connection,
        object_type="recommendation_set",
        object_version_id=set_version_id,
        review_kind="clinical",
        actor_id=ids.PROFESSIONAL_A,
        moment=moment,
        content=dump(list(strategy_version_ids)),
    )
    connection.execute(
        "INSERT OR IGNORE INTO recommendation_set_versions(recommendation_set_version_id,"
        " recommendation_set_id, recommendation_set_version, applicability_predicate,"
        " ordered_strategy_version_ids, reviewed_priority, clinical_review_id, status,"
        " effective_from, suspended_at, content_sha256, created_at)"
        " VALUES (?, ?, '1', ?, ?, 1, ?, 'active', ?, NULL, ?, ?)",
        (
            set_version_id,
            set_id,
            dump(data.SET_PREDICATE),
            dump(list(strategy_version_ids)),
            set_review_id,
            "2026-01-01T00:00:00.000Z",
            _sha("set:" + set_version_id),
            moment,
        ),
    )
    activation_review_id = _seed_authoring_review(
        connection,
        object_type="catalog",
        object_version_id=ids.CATALOG_FIXTURE,
        review_kind="catalog_activation",
        actor_id=ids.TENANT_ADMIN_A,
        moment=moment,
        content=dump([set_version_id]),
    )
    connection.execute(
        "INSERT OR IGNORE INTO catalog_versions(catalog_version, tenant_id, corpus_version,"
        " recommendation_set_version_ids, catalog_activation_review_id, status,"
        " effective_from, suspended_at, retired_at, content_sha256, created_at)"
        " VALUES (?, ?, ?, ?, ?, 'active', ?, NULL, NULL, ?, ?)",
        (
            ids.CATALOG_FIXTURE,
            ids.TENANT_A,
            ids.CORPUS_FIXTURE,
            dump([set_version_id]),
            activation_review_id,
            "2026-01-01T00:00:00.000Z",
            _sha("catalog:" + ids.CATALOG_FIXTURE),
            moment,
        ),
    )
    return ids.CATALOG_FIXTURE


def summary(result: SeedResult) -> dict[str, Any]:
    return {
        "catalog_profile": result.catalog_profile,
        "catalog_version": result.catalog_version,
        "catalog_status": (
            "catalog_fixture_active"
            if result.catalog_profile == "fixture-active"
            else "blocked_clinical_review"
        ),
        "strategy_version_ids": list(result.strategy_version_ids),
        "demo_tokens": result.tokens,
    }
