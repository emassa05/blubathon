-- 003_corpus_catalog_recommendations
-- Corpus versionado, estrategias con citas, sets, catálogos, instancias de
-- recomendación, reviews por estrategia, planes humanos, ejecuciones y
-- solicitudes de autoría.
--
-- El corpus vive en su propio almacenamiento en piloto. En la demo
-- comparte archivo pero no comparte claves con datos clínicos: ninguna tabla de
-- corpus referencia `subjects`.

CREATE TABLE corpus_versions (
    corpus_version   TEXT PRIMARY KEY,
    status           TEXT NOT NULL CHECK (status IN
                         ('draft', 'reviewed', 'active', 'suspended', 'retired')),
    effective_from   TEXT NOT NULL,
    suspended_at     TEXT,
    retired_at       TEXT,
    content_sha256   TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE document_versions (
    document_version_id      TEXT PRIMARY KEY,
    source_id                TEXT NOT NULL,
    publisher                TEXT NOT NULL,
    title                    TEXT NOT NULL,
    document_version         TEXT NOT NULL,
    publication_date         TEXT NOT NULL,
    retrieved_at             TEXT NOT NULL,
    canonical_url            TEXT NOT NULL,
    rights_basis             TEXT NOT NULL,
    original_bytes_sha256    TEXT NOT NULL,
    extracted_text_sha256    TEXT NOT NULL,
    extraction_manifest_id   TEXT NOT NULL,
    language                 TEXT NOT NULL,
    status                   TEXT NOT NULL CHECK (status IN
                                 ('draft', 'verified', 'indexed', 'active',
                                  'superseded', 'withdrawn')),
    corpus_version           TEXT REFERENCES corpus_versions(corpus_version),
    created_at               TEXT NOT NULL,
    UNIQUE (source_id, document_version)
);

CREATE TABLE document_chunks (
    document_chunk_id    TEXT PRIMARY KEY,
    document_version_id  TEXT NOT NULL REFERENCES document_versions(document_version_id),
    locator              TEXT NOT NULL,
    text                 TEXT NOT NULL,
    chunk_sha256         TEXT NOT NULL,
    chunker_version      TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    UNIQUE (document_version_id, locator)
);

CREATE TABLE authoring_build_manifests (
    authoring_build_manifest_id  TEXT PRIMARY KEY,
    corpus_version               TEXT REFERENCES corpus_versions(corpus_version),
    retrieval_mode               TEXT NOT NULL CHECK (retrieval_mode IN
                                     ('hybrid', 'lexical_only')),
    payload                      TEXT NOT NULL,
    content_sha256               TEXT NOT NULL,
    created_at                   TEXT NOT NULL
);

CREATE TABLE authoring_reviews (
    authoring_review_id      TEXT PRIMARY KEY,
    tenant_id                TEXT REFERENCES tenants(tenant_id),
    object_type              TEXT NOT NULL CHECK (object_type IN (
                                 'target_definition', 'document', 'strategy',
                                 'recommendation_set', 'catalog')),
    object_version_id        TEXT NOT NULL,
    review_kind              TEXT NOT NULL CHECK (review_kind IN (
                                 'evidence', 'clinical', 'privacy', 'catalog_activation')),
    actor_id                 TEXT NOT NULL REFERENCES users(user_id),
    accreditation_id         TEXT NOT NULL
                                 REFERENCES professional_accreditations(accreditation_id),
    decision                 TEXT NOT NULL CHECK (decision IN
                                 ('approved', 'changes_requested', 'rejected')),
    reviewed_content_sha256  TEXT NOT NULL,
    reviewed_at              TEXT NOT NULL,
    supersedes_id            TEXT REFERENCES authoring_reviews(authoring_review_id),
    ingested_at              TEXT NOT NULL
);

CREATE INDEX ix_authoring_reviews_object
    ON authoring_reviews(object_type, object_version_id, review_kind);

CREATE TABLE strategies (
    strategy_id  TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL
);

CREATE TABLE strategy_versions (
    strategy_version_id     TEXT PRIMARY KEY,
    strategy_id             TEXT NOT NULL REFERENCES strategies(strategy_id),
    purpose_es              TEXT NOT NULL,
    action_text_es          TEXT NOT NULL,
    claims                  TEXT NOT NULL,
    applicability_predicate TEXT NOT NULL,
    required_approver_role  TEXT NOT NULL,
    allowed_executor_roles  TEXT NOT NULL,
    corpus_version          TEXT REFERENCES corpus_versions(corpus_version),
    evidence_review_id      TEXT REFERENCES authoring_reviews(authoring_review_id),
    clinical_review_id      TEXT REFERENCES authoring_reviews(authoring_review_id),
    effective_from          TEXT NOT NULL,
    supersedes_version_id   TEXT REFERENCES strategy_versions(strategy_version_id),
    status                  TEXT NOT NULL CHECK (status IN (
                                'draft', 'evidence_reviewed', 'clinical_reviewed',
                                'active', 'suspended', 'retired')),
    suspended_at            TEXT,
    content_sha256          TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    CHECK (status <> 'active'
        OR (evidence_review_id IS NOT NULL AND clinical_review_id IS NOT NULL))
);

CREATE TABLE strategy_citations (
    citation_id          TEXT PRIMARY KEY,
    strategy_version_id  TEXT NOT NULL REFERENCES strategy_versions(strategy_version_id),
    claim_id             TEXT NOT NULL,
    document_chunk_id    TEXT NOT NULL REFERENCES document_chunks(document_chunk_id),
    locator              TEXT NOT NULL,
    quoted_text          TEXT NOT NULL,
    quoted_text_sha256   TEXT NOT NULL,
    canonical_url        TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE INDEX ix_citations_version ON strategy_citations(strategy_version_id, claim_id);

CREATE TABLE recommendation_sets (
    recommendation_set_id  TEXT PRIMARY KEY,
    tenant_id              TEXT REFERENCES tenants(tenant_id),
    created_at             TEXT NOT NULL
);

CREATE TABLE recommendation_set_versions (
    recommendation_set_version_id TEXT PRIMARY KEY,
    recommendation_set_id         TEXT NOT NULL
                                      REFERENCES recommendation_sets(recommendation_set_id),
    recommendation_set_version    TEXT NOT NULL,
    applicability_predicate       TEXT NOT NULL,
    ordered_strategy_version_ids  TEXT NOT NULL,
    reviewed_priority             INTEGER NOT NULL,
    clinical_review_id            TEXT REFERENCES authoring_reviews(authoring_review_id),
    status                        TEXT NOT NULL CHECK (status IN
                                      ('draft', 'reviewed', 'active', 'suspended', 'retired')),
    effective_from                TEXT NOT NULL,
    suspended_at                  TEXT,
    content_sha256                TEXT NOT NULL,
    created_at                    TEXT NOT NULL,
    UNIQUE (recommendation_set_id, recommendation_set_version)
);

CREATE TABLE catalog_versions (
    catalog_version                 TEXT PRIMARY KEY,
    tenant_id                       TEXT NOT NULL REFERENCES tenants(tenant_id),
    corpus_version                  TEXT REFERENCES corpus_versions(corpus_version),
    recommendation_set_version_ids  TEXT NOT NULL,
    catalog_activation_review_id    TEXT REFERENCES authoring_reviews(authoring_review_id),
    status                          TEXT NOT NULL CHECK (status IN
                                        ('draft', 'reviewed', 'active', 'suspended', 'retired')),
    effective_from                  TEXT NOT NULL,
    suspended_at                    TEXT,
    retired_at                      TEXT,
    content_sha256                  TEXT NOT NULL,
    created_at                      TEXT NOT NULL,
    CHECK (status <> 'active' OR catalog_activation_review_id IS NOT NULL)
);

CREATE UNIQUE INDEX ux_catalog_active_effective
    ON catalog_versions(tenant_id, effective_from) WHERE status = 'active';

CREATE TABLE recommendation_instances (
    recommendation_instance_id  TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                  TEXT NOT NULL REFERENCES subjects(subject_id),
    prediction_episode_id       TEXT NOT NULL UNIQUE
                                    REFERENCES prediction_episodes(prediction_episode_id),
    scenario_hash               TEXT NOT NULL,
    scenario_schema_version     TEXT NOT NULL,
    scenario_builder_version    TEXT NOT NULL,
    encrypted_scenario          BLOB NOT NULL,
    catalog_version             TEXT REFERENCES catalog_versions(catalog_version),
    corpus_version              TEXT REFERENCES corpus_versions(corpus_version),
    strategy_version_ids        TEXT NOT NULL,
    runtime_status              TEXT NOT NULL CHECK (runtime_status IN ('matched', 'abstained')),
    abstention_reasons          TEXT NOT NULL,
    availability_reason         TEXT NOT NULL,
    created_at                  TEXT NOT NULL,
    CHECK (runtime_status <> 'abstained' OR strategy_version_ids = '[]')
);

CREATE INDEX ix_instances_inbox
    ON recommendation_instances(tenant_id, subject_id, created_at);

CREATE TABLE human_plan_versions (
    human_plan_version_id   TEXT PRIMARY KEY,
    tenant_id               TEXT NOT NULL REFERENCES tenants(tenant_id),
    recommendation_instance_id TEXT NOT NULL
                                REFERENCES recommendation_instances(recommendation_instance_id),
    replaced_strategy_version_id TEXT NOT NULL
                                REFERENCES strategy_versions(strategy_version_id),
    action_text_es          TEXT NOT NULL,
    author_actor_id         TEXT NOT NULL REFERENCES users(user_id),
    allowed_executor_roles  TEXT NOT NULL,
    plan_version            INTEGER NOT NULL,
    content_sha256          TEXT NOT NULL,
    created_at              TEXT NOT NULL
);

CREATE INDEX ix_human_plans_instance ON human_plan_versions(recommendation_instance_id);

CREATE TABLE recommendation_reviews (
    review_id                   TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL REFERENCES tenants(tenant_id),
    recommendation_instance_id  TEXT NOT NULL
                                    REFERENCES recommendation_instances(recommendation_instance_id),
    strategy_version_id         TEXT NOT NULL REFERENCES strategy_versions(strategy_version_id),
    decision                    TEXT NOT NULL CHECK (decision IN (
                                    'approved', 'rejected', 'human_plan_substituted',
                                    'not_applicable', 'deferred')),
    reviewed_by                 TEXT NOT NULL REFERENCES users(user_id),
    reviewer_role               TEXT NOT NULL,
    reviewed_at                 TEXT NOT NULL,
    human_plan_version_id       TEXT REFERENCES human_plan_versions(human_plan_version_id),
    supersedes_id               TEXT REFERENCES recommendation_reviews(review_id),
    ingested_at                 TEXT NOT NULL,
    CHECK ((decision = 'human_plan_substituted' AND human_plan_version_id IS NOT NULL)
        OR (decision <> 'human_plan_substituted' AND human_plan_version_id IS NULL))
);

CREATE INDEX ix_reviews_instance
    ON recommendation_reviews(recommendation_instance_id, strategy_version_id, reviewed_at);
CREATE UNIQUE INDEX ux_reviews_supersedes
    ON recommendation_reviews(supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE strategy_executions (
    strategy_execution_id       TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL REFERENCES tenants(tenant_id),
    recommendation_instance_id  TEXT NOT NULL
                                    REFERENCES recommendation_instances(recommendation_instance_id),
    strategy_version_id         TEXT REFERENCES strategy_versions(strategy_version_id),
    human_plan_version_id       TEXT REFERENCES human_plan_versions(human_plan_version_id),
    status                      TEXT NOT NULL CHECK (status IN
                                    ('applied', 'not_applied', 'unknown')),
    actor_id                    TEXT NOT NULL REFERENCES users(user_id),
    actor_role                  TEXT NOT NULL,
    recorded_at                 TEXT NOT NULL,
    applied_at                  TEXT,
    supersedes_id               TEXT REFERENCES strategy_executions(strategy_execution_id),
    ingested_at                 TEXT NOT NULL,
    CHECK ((strategy_version_id IS NOT NULL) <> (human_plan_version_id IS NOT NULL)),
    CHECK (applied_at IS NULL OR applied_at <= recorded_at),
    CHECK (status <> 'applied' OR applied_at IS NOT NULL)
);

CREATE INDEX ix_executions_instance
    ON strategy_executions(recommendation_instance_id, recorded_at);
CREATE UNIQUE INDEX ux_executions_supersedes
    ON strategy_executions(supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE authoring_requests (
    authoring_request_id    TEXT PRIMARY KEY,
    tenant_id               TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id              TEXT NOT NULL REFERENCES subjects(subject_id),
    prediction_episode_id   TEXT NOT NULL REFERENCES prediction_episodes(prediction_episode_id),
    scenario_hash           TEXT NOT NULL,
    scenario_schema_version TEXT NOT NULL,
    encrypted_scenario      BLOB NOT NULL,
    reason                  TEXT NOT NULL,
    catalog_version         TEXT REFERENCES catalog_versions(catalog_version),
    status                  TEXT NOT NULL CHECK (status IN ('open', 'exported', 'closed')),
    created_at              TEXT NOT NULL,
    closed_at               TEXT
);

CREATE UNIQUE INDEX ux_authoring_requests_open
    ON authoring_requests(tenant_id, subject_id, scenario_hash, COALESCE(catalog_version, ''))
    WHERE status = 'open';

CREATE TABLE authoring_use_authorizations (
    authorization_id            TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                  TEXT NOT NULL REFERENCES subjects(subject_id),
    authoring_request_id        TEXT NOT NULL REFERENCES authoring_requests(authoring_request_id),
    basis_type                  TEXT NOT NULL CHECK (basis_type IN
                                    ('consent', 'institutional_legal_basis')),
    consent_id                  TEXT REFERENCES consents(consent_id),
    legal_basis_version         TEXT,
    scope                       TEXT NOT NULL CHECK (scope = 'generalize_query_only'),
    approved_by_privacy_reviewer TEXT NOT NULL REFERENCES users(user_id),
    approved_at                 TEXT NOT NULL,
    valid_from                  TEXT NOT NULL,
    valid_until                 TEXT,
    revoked_at                  TEXT,
    status                      TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    supersedes_id               TEXT REFERENCES authoring_use_authorizations(authorization_id),
    ingested_at                 TEXT NOT NULL,
    CHECK ((basis_type = 'consent' AND consent_id IS NOT NULL)
        OR (basis_type = 'institutional_legal_basis' AND legal_basis_version IS NOT NULL))
);
