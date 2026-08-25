-- 002_form_prediction_outcome
-- Target versionado, sesiones de formulario, observaciones append-only,
-- episodios primarios no solapados, snapshots, outputs por track y la cadena
-- reporte -> resolución -> adjudicación. SPEC 4, 5.2, 5.8, 11.3-11.5 y 12.1.

CREATE TABLE target_definition_versions (
    target_definition_version  TEXT PRIMARY KEY,
    scope                      TEXT NOT NULL CHECK (scope IN ('tenant', 'demo_fixture')),
    tenant_id                  TEXT REFERENCES tenants(tenant_id),
    question_es                TEXT NOT NULL,
    severity_anchors_es        TEXT NOT NULL,
    eligible_reporter_roles    TEXT NOT NULL,
    eligible_source_mappings   TEXT NOT NULL,
    effective_from             TEXT NOT NULL,
    retired_at                 TEXT,
    evidence_basis             TEXT NOT NULL,
    approval_status            TEXT NOT NULL CHECK (approval_status IN
                                   ('draft', 'active', 'retired')),
    clinical_review_id         TEXT,
    content_sha256             TEXT NOT NULL,
    ingested_at                TEXT NOT NULL,
    -- SPEC 4.3: `scope=tenant` exige tenant; `demo_fixture` lo prohíbe.
    CHECK ((scope = 'tenant' AND tenant_id IS NOT NULL)
        OR (scope = 'demo_fixture' AND tenant_id IS NULL))
);

-- Unicidad efectiva fail-closed: dos versiones activas no pueden compartir
-- scope, tenant y `effective_from`. Si sus vigencias se solapan igualmente, la
-- selección devuelve `target_definition_ambiguous` (SPEC 4.3).
CREATE UNIQUE INDEX ux_target_active_effective
    ON target_definition_versions(scope, COALESCE(tenant_id, ''), effective_from)
    WHERE approval_status = 'active';

CREATE TABLE form_sessions (
    form_session_id             TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                  TEXT NOT NULL REFERENCES subjects(subject_id),
    actor_id                    TEXT NOT NULL REFERENCES users(user_id),
    source                      TEXT NOT NULL CHECK (source IN ('home', 'therapy', 'school')),
    session_kind                TEXT NOT NULL CHECK (session_kind IN
                                    ('caregiver_daily', 'professional_observation')),
    status                      TEXT NOT NULL CHECK (status IN
                                    ('draft', 'submitted', 'abandoned', 'expired')),
    -- SPEC 6.8 / INV-05: se fija al abrir y no se recalcula jamás.
    audit_mode                  INTEGER NOT NULL CHECK (audit_mode IN (0, 1)),
    audit_bucket                INTEGER NOT NULL,
    form_policy_version         TEXT NOT NULL,
    local_date                  TEXT NOT NULL,
    opened_at                   TEXT NOT NULL,
    submitted_at                TEXT,
    prediction_status           TEXT CHECK (prediction_status IN (
                                    'episode_created', 'episode_linked',
                                    'target_definition_unavailable',
                                    'target_definition_ambiguous')),
    prediction_episode_id       TEXT,
    linked_prediction_episode_id TEXT,
    -- SPEC 4.1: `submitted_at` nunca precede a `opened_at`.
    CHECK (submitted_at IS NULL OR submitted_at >= opened_at),
    CHECK (status <> 'submitted' OR submitted_at IS NOT NULL),
    -- Una sesión enlaza o crea, nunca ambas.
    CHECK (prediction_episode_id IS NULL OR linked_prediction_episode_id IS NULL)
);

CREATE INDEX ix_form_sessions_subject
    ON form_sessions(tenant_id, subject_id, opened_at);

CREATE TABLE default_presentations (
    default_presentation_id  TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id               TEXT NOT NULL REFERENCES subjects(subject_id),
    form_session_id          TEXT NOT NULL REFERENCES form_sessions(form_session_id),
    field_code               TEXT NOT NULL,
    candidate_value          TEXT NOT NULL,
    candidate_count          INTEGER NOT NULL,
    posterior_mean           REAL NOT NULL,
    lower_bound              REAL NOT NULL,
    n_observations           INTEGER NOT NULL,
    estimator_version        TEXT NOT NULL,
    presented_at             TEXT NOT NULL,
    superseded_at            TEXT,
    UNIQUE (form_session_id, field_code, presented_at)
);

CREATE INDEX ix_default_presentations_session
    ON default_presentations(form_session_id, field_code);

CREATE TABLE question_presentations (
    question_presentation_id  TEXT PRIMARY KEY,
    tenant_id                 TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                TEXT NOT NULL REFERENCES subjects(subject_id),
    form_session_id           TEXT NOT NULL REFERENCES form_sessions(form_session_id),
    field_code                TEXT NOT NULL,
    -- SPEC 6.10: solo `highlighted=1` reinicia el reloj de antigüedad.
    highlighted               INTEGER NOT NULL CHECK (highlighted IN (0, 1)),
    reason                    TEXT NOT NULL,
    voi_nats                  REAL,
    position                  INTEGER NOT NULL,
    source                    TEXT NOT NULL,
    local_date                TEXT NOT NULL,
    presented_at              TEXT NOT NULL,
    UNIQUE (form_session_id, field_code)
);

CREATE INDEX ix_question_presentations_staleness
    ON question_presentations(tenant_id, subject_id, field_code, highlighted, local_date);

CREATE TABLE field_observations (
    field_observation_id  TEXT PRIMARY KEY,
    tenant_id             TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id            TEXT NOT NULL REFERENCES subjects(subject_id),
    form_session_id       TEXT REFERENCES form_sessions(form_session_id),
    field_code            TEXT NOT NULL,
    -- JSON canónico del valor, o NULL para `explicit_unknown` (SPEC 8.2).
    value                 TEXT,
    source                TEXT NOT NULL CHECK (source IN ('home', 'therapy', 'school')),
    actor_id              TEXT NOT NULL REFERENCES users(user_id),
    entry_mode            TEXT NOT NULL CHECK (entry_mode IN (
                              'manual_no_default', 'audit_manual', 'default_accepted',
                              'default_edited', 'professional_observed',
                              'imported_observed', 'explicit_unknown')),
    data_origin           TEXT NOT NULL CHECK (data_origin IN ('real', 'synthetic')),
    cohort_kind           TEXT NOT NULL CHECK (cohort_kind IN ('real_subject', 'demo_fixture')),
    effective_at          TEXT NOT NULL,
    ingested_at           TEXT NOT NULL,
    local_date            TEXT NOT NULL,
    source_mapping_id     TEXT REFERENCES source_mappings(source_mapping_id),
    default_presentation_id TEXT REFERENCES default_presentations(default_presentation_id),
    supersedes_id         TEXT REFERENCES field_observations(field_observation_id),
    -- SPEC 8.2: `explicit_unknown` no asigna valor; el resto sí.
    CHECK ((entry_mode = 'explicit_unknown' AND value IS NULL)
        OR (entry_mode <> 'explicit_unknown' AND value IS NOT NULL)),
    -- SPEC 4.4: una importación exige mapping aprobado.
    CHECK (entry_mode <> 'imported_observed' OR source_mapping_id IS NOT NULL)
);

CREATE INDEX ix_field_observations_window
    ON field_observations(tenant_id, subject_id, field_code, source, local_date);
CREATE INDEX ix_field_observations_session
    ON field_observations(form_session_id, field_code);
CREATE UNIQUE INDEX ux_field_observations_supersedes
    ON field_observations(supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE prediction_episodes (
    prediction_episode_id      TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    form_session_id            TEXT NOT NULL REFERENCES form_sessions(form_session_id),
    role                       TEXT NOT NULL CHECK (role IN ('primary', 'secondary')),
    status                     TEXT NOT NULL CHECK (status IN
                                   ('pending', 'completed', 'failed')),
    as_of_at                   TEXT NOT NULL,
    prediction_at              TEXT NOT NULL,
    target_start_at            TEXT NOT NULL,
    target_end_at              TEXT NOT NULL,
    capture_deadline_at        TEXT NOT NULL,
    target_definition_version  TEXT NOT NULL
                                   REFERENCES target_definition_versions(target_definition_version),
    profile_version            TEXT,
    care_mode                  TEXT,
    input_data_origin          TEXT NOT NULL CHECK (input_data_origin IN ('real', 'synthetic')),
    created_at                 TEXT NOT NULL,
    -- SPEC 4.1: as_of_at = prediction_at = target_start_at = submitted_at.
    CHECK (as_of_at = prediction_at AND prediction_at = target_start_at),
    CHECK (target_end_at > target_start_at),
    CHECK (capture_deadline_at > target_end_at)
);

-- SPEC 4.2: dos episodios primarios del mismo sujeto no pueden empezar en el
-- mismo instante. El solape se comprueba además dentro de la transacción
-- serializada por (tenant_id, subject_id).
CREATE UNIQUE INDEX ux_primary_episode_start
    ON prediction_episodes(tenant_id, subject_id, target_start_at)
    WHERE role = 'primary';
CREATE INDEX ix_episodes_open_primary
    ON prediction_episodes(tenant_id, subject_id, role, target_end_at);
CREATE UNIQUE INDEX ux_episode_per_session ON prediction_episodes(form_session_id);

CREATE TABLE feature_snapshots (
    feature_snapshot_id       TEXT PRIMARY KEY,
    tenant_id                 TEXT NOT NULL REFERENCES tenants(tenant_id),
    prediction_episode_id     TEXT NOT NULL UNIQUE
                                  REFERENCES prediction_episodes(prediction_episode_id),
    as_of_at                  TEXT NOT NULL,
    input_data_origin         TEXT NOT NULL CHECK (input_data_origin IN ('real', 'synthetic')),
    -- SPEC 5.8: el snapshot persiste los IDs exactos proyectados.
    projected_observation_ids TEXT NOT NULL,
    projected_outcome_ids     TEXT NOT NULL,
    consent_ids               TEXT NOT NULL,
    profile_version           TEXT,
    care_mode                 TEXT,
    content_sha256            TEXT NOT NULL,
    created_at                TEXT NOT NULL
);

CREATE TABLE prediction_outputs (
    prediction_output_id   TEXT PRIMARY KEY,
    tenant_id              TEXT NOT NULL REFERENCES tenants(tenant_id),
    prediction_episode_id  TEXT NOT NULL REFERENCES prediction_episodes(prediction_episode_id),
    track_id               TEXT NOT NULL,
    intended_use           TEXT NOT NULL,
    status                 TEXT NOT NULL CHECK (status IN ('ok', 'abstained', 'unavailable')),
    estimate_kind          TEXT NOT NULL,
    probability            REAL,
    simulation_score       REAL,
    interval_low           REAL,
    interval_high          REAL,
    interval_method        TEXT,
    abstention_reasons     TEXT NOT NULL,
    model_version          TEXT NOT NULL,
    input_data_origin      TEXT NOT NULL CHECK (input_data_origin IN ('real', 'synthetic')),
    -- SPEC 8.5: el challenger nunca se expone, ni siquiera al profesional.
    exposed                INTEGER NOT NULL CHECK (exposed IN (0, 1)),
    created_at             TEXT NOT NULL,
    UNIQUE (prediction_episode_id, track_id),
    -- SPEC 11.5: una abstención anula probabilidad, score, intervalo y método.
    CHECK (status <> 'abstained' OR (probability IS NULL AND simulation_score IS NULL
        AND interval_low IS NULL AND interval_high IS NULL AND interval_method IS NULL)),
    CHECK (interval_low IS NULL OR (interval_high IS NOT NULL AND interval_high >= interval_low)),
    CHECK ((interval_low IS NULL) = (interval_high IS NULL)),
    -- SPEC 8.6: v0.3 no tiene bandas ni política de decisión.
    CHECK (probability IS NULL OR (probability >= 0.0 AND probability <= 1.0)),
    CHECK (simulation_score IS NULL OR (simulation_score >= 0.0 AND simulation_score <= 1.0))
);

CREATE INDEX ix_outputs_episode ON prediction_outputs(prediction_episode_id);

CREATE TABLE outcome_requests (
    outcome_request_id         TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    -- SPEC 4.2: como máximo un request por episodio primario.
    prediction_episode_id      TEXT NOT NULL UNIQUE
                                   REFERENCES prediction_episodes(prediction_episode_id),
    target_definition_version  TEXT NOT NULL
                                   REFERENCES target_definition_versions(target_definition_version),
    target_start_at            TEXT NOT NULL,
    target_end_at              TEXT NOT NULL,
    capture_deadline_at        TEXT NOT NULL,
    eligible_reporter_roles    TEXT NOT NULL,
    created_at                 TEXT NOT NULL
);

CREATE INDEX ix_outcome_requests_inbox
    ON outcome_requests(tenant_id, subject_id, capture_deadline_at);

CREATE TABLE outcome_reports (
    outcome_report_id          TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    prediction_episode_id      TEXT NOT NULL REFERENCES prediction_episodes(prediction_episode_id),
    target_definition_version  TEXT NOT NULL
                                   REFERENCES target_definition_versions(target_definition_version),
    reporter_actor_id          TEXT NOT NULL REFERENCES users(user_id),
    reporter_role              TEXT NOT NULL,
    value                      TEXT NOT NULL CHECK (value IN ('yes', 'no', 'unknown')),
    occurred_at                TEXT,
    reported_at                TEXT NOT NULL,
    timing_status              TEXT NOT NULL CHECK (timing_status IN
                                   ('early', 'on_time', 'late')),
    data_origin                TEXT NOT NULL CHECK (data_origin IN ('real', 'synthetic')),
    intake_channel             TEXT NOT NULL CHECK (intake_channel IN ('form', 'import')),
    source_mapping_id          TEXT REFERENCES source_mappings(source_mapping_id),
    supersedes_id              TEXT REFERENCES outcome_reports(outcome_report_id),
    ingested_at                TEXT NOT NULL,
    -- SPEC 4.4: `yes` exige `occurred_at <= reported_at`; `no`/`unknown` lo prohíben.
    CHECK ((value = 'yes' AND occurred_at IS NOT NULL AND occurred_at <= reported_at)
        OR (value IN ('no', 'unknown') AND occurred_at IS NULL)),
    CHECK (intake_channel <> 'import' OR source_mapping_id IS NOT NULL),
    CHECK (intake_channel <> 'form' OR source_mapping_id IS NULL)
);

CREATE INDEX ix_outcome_reports_episode
    ON outcome_reports(prediction_episode_id, reported_at, outcome_report_id);
CREATE UNIQUE INDEX ux_outcome_reports_supersedes
    ON outcome_reports(supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE outcome_resolutions (
    outcome_resolution_id  TEXT PRIMARY KEY,
    tenant_id              TEXT NOT NULL REFERENCES tenants(tenant_id),
    prediction_episode_id  TEXT NOT NULL REFERENCES prediction_episodes(prediction_episode_id),
    status                 TEXT NOT NULL CHECK (status IN
                               ('pending', 'yes', 'no', 'unknown', 'conflicted')),
    resolved_at            TEXT,
    qualifying_report_id   TEXT REFERENCES outcome_reports(outcome_report_id),
    -- SPEC 4.4: monotónico entre versiones; nunca vuelve a 0.
    ever_conflicted        INTEGER NOT NULL CHECK (ever_conflicted IN (0, 1)),
    resolution_version     INTEGER NOT NULL,
    ingested_at            TEXT NOT NULL,
    supersedes_id          TEXT REFERENCES outcome_resolutions(outcome_resolution_id),
    UNIQUE (prediction_episode_id, resolution_version),
    CHECK (status <> 'pending' OR resolved_at IS NULL),
    CHECK (status NOT IN ('yes', 'no') OR qualifying_report_id IS NOT NULL)
);

CREATE INDEX ix_outcome_resolutions_active
    ON outcome_resolutions(prediction_episode_id, resolution_version DESC);

CREATE TABLE outcome_adjudications (
    outcome_adjudication_id  TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL REFERENCES tenants(tenant_id),
    prediction_episode_id    TEXT NOT NULL REFERENCES prediction_episodes(prediction_episode_id),
    actor_id                 TEXT NOT NULL REFERENCES users(user_id),
    decision                 TEXT NOT NULL,
    reason                   TEXT NOT NULL,
    decided_at               TEXT NOT NULL,
    ingested_at              TEXT NOT NULL
);

CREATE INDEX ix_adjudications_episode ON outcome_adjudications(prediction_episode_id);
