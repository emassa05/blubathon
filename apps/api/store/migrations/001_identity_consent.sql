-- 001_identity_consent
-- Identidad, roles, acreditaciones, sujetos, perfiles, grants y consentimientos.
-- Todo contrato de autorización es append-only: una
-- corrección crea otra fila con `supersedes_id`, nunca un UPDATE destructivo.
--
-- Los timestamps se guardan en el formato canónico `YYYY-MM-DDTHH:mm:ss.sssZ`
-- para que el orden lexicográfico sea el orden cronológico.

CREATE TABLE tenants (
    tenant_id        TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    deployment_mode  TEXT NOT NULL CHECK (deployment_mode IN ('demo', 'pilot')),
    created_at       TEXT NOT NULL
);

CREATE TABLE users (
    user_id             TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants(tenant_id),
    display_name        TEXT NOT NULL,
    demo_session_token  TEXT UNIQUE,
    created_at          TEXT NOT NULL
);

CREATE INDEX ix_users_tenant ON users(tenant_id);

CREATE TABLE user_roles (
    user_role_id  TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenants(tenant_id),
    user_id       TEXT NOT NULL REFERENCES users(user_id),
    role          TEXT NOT NULL CHECK (role IN (
                      'caregiver', 'professional', 'clinical_reviewer',
                      'evidence_reviewer', 'privacy_reviewer', 'model_evaluator',
                      'tenant_admin', 'auditor')),
    granted_at    TEXT NOT NULL,
    UNIQUE (user_id, role)
);

CREATE INDEX ix_user_roles_lookup ON user_roles(tenant_id, user_id);

CREATE TABLE professional_accreditations (
    accreditation_id           TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    actor_id                   TEXT NOT NULL REFERENCES users(user_id),
    capabilities               TEXT NOT NULL,
    credential_policy_version  TEXT NOT NULL,
    issuer_actor_id            TEXT NOT NULL REFERENCES users(user_id),
    valid_from                 TEXT NOT NULL,
    valid_until                TEXT,
    revoked_at                 TEXT,
    status                     TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    supersedes_id              TEXT REFERENCES professional_accreditations(accreditation_id),
    ingested_at                TEXT NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX ix_accreditations_actor ON professional_accreditations(tenant_id, actor_id);

CREATE TABLE subjects (
    subject_id     TEXT PRIMARY KEY,
    tenant_id      TEXT NOT NULL REFERENCES tenants(tenant_id),
    display_label  TEXT NOT NULL,
    cohort_kind    TEXT NOT NULL CHECK (cohort_kind IN ('real_subject', 'demo_fixture')),
    created_at     TEXT NOT NULL
);

CREATE INDEX ix_subjects_tenant ON subjects(tenant_id, cohort_kind);

CREATE TABLE subject_profiles (
    subject_profile_id         TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    sensory_profile_tags       TEXT NOT NULL,
    communication_support_tags TEXT NOT NULL,
    contraindication_tags      TEXT NOT NULL,
    care_mode                  TEXT NOT NULL,
    profile_version            TEXT NOT NULL,
    effective_from             TEXT NOT NULL,
    recorded_at                TEXT NOT NULL,
    supersedes_id              TEXT REFERENCES subject_profiles(subject_profile_id),
    ingested_at                TEXT NOT NULL,
    UNIQUE (subject_id, profile_version)
);

CREATE INDEX ix_subject_profiles_lookup
    ON subject_profiles(tenant_id, subject_id, effective_from);

CREATE TABLE subject_access_grants (
    subject_access_grant_id  TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id               TEXT NOT NULL REFERENCES subjects(subject_id),
    actor_id                 TEXT NOT NULL REFERENCES users(user_id),
    capabilities             TEXT NOT NULL,
    issuer_actor_id          TEXT NOT NULL REFERENCES users(user_id),
    valid_from               TEXT NOT NULL,
    valid_until              TEXT,
    revoked_at               TEXT,
    status                   TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    supersedes_id            TEXT REFERENCES subject_access_grants(subject_access_grant_id),
    ingested_at              TEXT NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX ix_grants_actor ON subject_access_grants(tenant_id, actor_id, subject_id);
CREATE INDEX ix_grants_subject ON subject_access_grants(tenant_id, subject_id);

CREATE TABLE consents (
    consent_id        TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id        TEXT NOT NULL REFERENCES subjects(subject_id),
    grantor_actor_id  TEXT NOT NULL REFERENCES users(user_id),
    purpose           TEXT NOT NULL CHECK (purpose IN (
                          'operational_support', 'secondary_model_use',
                          'authoring_generalization')),
    policy_version    TEXT NOT NULL,
    granted_at        TEXT NOT NULL,
    valid_from        TEXT NOT NULL,
    valid_until       TEXT,
    revoked_at        TEXT,
    status            TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    supersedes_id     TEXT REFERENCES consents(consent_id),
    ingested_at       TEXT NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX ix_consents_lookup ON consents(tenant_id, subject_id, purpose);

CREATE TABLE source_mappings (
    source_mapping_id  TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL REFERENCES tenants(tenant_id),
    name               TEXT NOT NULL,
    mapping_version    TEXT NOT NULL,
    approval_status    TEXT NOT NULL CHECK (approval_status IN ('draft', 'approved', 'retired')),
    content_sha256     TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    UNIQUE (tenant_id, name, mapping_version)
);
