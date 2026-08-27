-- 004_training_evaluation_audit
-- Volante de datos, evaluación versionada, auditoría append-only e idempotencia.
-- SPEC 10.5, 12.1, 12.2, 13.2 y 14.
--
-- La API importa manifests de P1; no entrena dentro del proceso HTTP.

CREATE TABLE dataset_snapshots (
    dataset_snapshot_id        TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    -- SPEC 10.5 / INV-17: sintético y real usan snapshots separados.
    data_origin                TEXT NOT NULL CHECK (data_origin IN ('real', 'synthetic')),
    target_definition_version  TEXT
                                   REFERENCES target_definition_versions(target_definition_version),
    cutoff_at                  TEXT NOT NULL,
    episode_ids                TEXT NOT NULL,
    observation_ids            TEXT NOT NULL,
    outcome_ids                TEXT NOT NULL,
    consent_ids                TEXT NOT NULL,
    subject_ids                TEXT NOT NULL,
    content_sha256             TEXT NOT NULL,
    created_at                 TEXT NOT NULL
);

CREATE TABLE training_runs (
    training_run_id      TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL REFERENCES tenants(tenant_id),
    dataset_snapshot_id  TEXT NOT NULL REFERENCES dataset_snapshots(dataset_snapshot_id),
    track_id             TEXT NOT NULL,
    protocol_version     TEXT NOT NULL,
    protocol_sha256      TEXT NOT NULL,
    status               TEXT NOT NULL CHECK (status IN
                             ('created', 'running', 'completed', 'not_trainable', 'failed')),
    reason               TEXT,
    code_reference       TEXT NOT NULL,
    dependency_manifest  TEXT NOT NULL,
    started_at           TEXT NOT NULL,
    finished_at          TEXT
);

CREATE TABLE model_versions (
    model_version          TEXT PRIMARY KEY,
    tenant_id              TEXT NOT NULL REFERENCES tenants(tenant_id),
    training_run_id        TEXT REFERENCES training_runs(training_run_id),
    track_id               TEXT NOT NULL,
    training_data_origin   TEXT NOT NULL CHECK (training_data_origin IN ('real', 'synthetic')),
    intended_use           TEXT NOT NULL,
    state                  TEXT NOT NULL CHECK (state IN (
                               'candidate', 'validated_offline', 'shadow',
                               'shadow_evaluated', 'rejected',
                               'suspended_for_consent_review', 'retired')),
    artifact_sha256        TEXT NOT NULL,
    created_at             TEXT NOT NULL,
    state_changed_at       TEXT NOT NULL
);

CREATE TABLE evaluation_reports (
    evaluation_report_id       TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    model_version              TEXT NOT NULL REFERENCES model_versions(model_version),
    dataset_snapshot_id        TEXT NOT NULL REFERENCES dataset_snapshots(dataset_snapshot_id),
    protocol_version           TEXT NOT NULL,
    target_definition_version  TEXT
                                   REFERENCES target_definition_versions(target_definition_version),
    data_origin                TEXT NOT NULL CHECK (data_origin IN ('real', 'synthetic')),
    status                     TEXT NOT NULL CHECK (status IN
                                   ('draft', 'published', 'suspended_for_consent_review',
                                    'retired')),
    -- JSON validado y versionado: métricas, estimabilidad y limitaciones.
    metrics                    TEXT NOT NULL,
    abstention_by_reason       TEXT NOT NULL,
    limitations_es             TEXT NOT NULL,
    dataset_sha256             TEXT NOT NULL,
    published_at               TEXT,
    created_at                 TEXT NOT NULL,
    UNIQUE (model_version, protocol_version)
);

CREATE INDEX ix_evaluation_reports_model ON evaluation_reports(model_version, status);

-- SPEC 13.2: la auditoría es append-only y no contiene payload clínico.
CREATE TABLE audit_events (
    audit_event_id  TEXT PRIMARY KEY,
    tenant_id       TEXT,
    actor_id        TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    subject_id      TEXT,
    decision        TEXT NOT NULL CHECK (decision IN ('allowed', 'denied')),
    reason_code     TEXT,
    request_id      TEXT NOT NULL,
    occurred_at     TEXT NOT NULL
);

CREATE INDEX ix_audit_events_lookup ON audit_events(tenant_id, occurred_at);
CREATE INDEX ix_audit_events_subject ON audit_events(subject_id, occurred_at);

-- SPEC 11.2 y CONVENTIONS 12.3. El scope incluye el path concreto normalizado:
-- dos IDs distintos nunca comparten replay.
CREATE TABLE idempotency_keys (
    idempotency_key_id       TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL REFERENCES tenants(tenant_id),
    actor_id                 TEXT NOT NULL REFERENCES users(user_id),
    method                   TEXT NOT NULL,
    normalized_concrete_path TEXT NOT NULL,
    idempotency_key          TEXT NOT NULL,
    request_sha256           TEXT NOT NULL,
    response_status          INTEGER NOT NULL,
    response_body            TEXT NOT NULL,
    created_at               TEXT NOT NULL,
    UNIQUE (tenant_id, actor_id, method, normalized_concrete_path, idempotency_key)
);
