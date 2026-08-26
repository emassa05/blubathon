DROP TABLE recommendation_instances;

CREATE TABLE recommendation_instances (
    recommendation_instance_id TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL REFERENCES tenants(tenant_id),
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    prediction_episode_id      TEXT NOT NULL UNIQUE
                                    REFERENCES prediction_episodes(prediction_episode_id),
    risk_band                  TEXT NOT NULL
                                    CHECK (risk_band IN ('low','medium','high','unknown')),
    query_es                   TEXT NOT NULL,
    status                     TEXT NOT NULL
                                    CHECK (status IN ('pending','matched','abstained')),
    action_text_es             TEXT,
    purpose_es                 TEXT,
    citations                  TEXT NOT NULL DEFAULT '[]',
    abstention_reason          TEXT
                                    CHECK (abstention_reason IN
                                        ('no_indexed_match','draft_unavailable','draft_not_grounded')
                                        OR abstention_reason IS NULL),
    attempt                    INTEGER NOT NULL DEFAULT 1,
    created_at                 TEXT NOT NULL,
    updated_at                 TEXT NOT NULL
);
CREATE INDEX ix_instances_inbox
    ON recommendation_instances(tenant_id, subject_id, created_at);

CREATE TABLE recommendation_feedback (
    feedback_id                TEXT PRIMARY KEY,
    recommendation_instance_id TEXT NOT NULL
                                    REFERENCES recommendation_instances(recommendation_instance_id),
    rating                     TEXT NOT NULL CHECK (rating IN ('good', 'bad')),
    note_es                    TEXT,
    created_at                 TEXT NOT NULL
);
CREATE INDEX ix_feedback_instance ON recommendation_feedback(recommendation_instance_id);
