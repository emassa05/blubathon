"""Migration shape and SQLite safety checks."""

from __future__ import annotations

import sqlite3

import pytest

from apps.api.canonical import canonical_timestamp
from apps.api.errors import BlubathonApiError
from apps.api.settings import Settings
from apps.api.store.db import Database, connect
from apps.api.store.migrations import MigrationError, discover, migrate
from tests.p2.conftest import START

SPEC_TABLES = {
    "audit_events",
    "authoring_build_manifests",
    "authoring_requests",
    "authoring_reviews",
    "authoring_use_authorizations",
    "catalog_versions",
    "consents",
    "corpus_versions",
    "dataset_snapshots",
    "default_presentations",
    "document_chunks",
    "document_versions",
    "evaluation_reports",
    "feature_snapshots",
    "field_observations",
    "form_sessions",
    "human_plan_versions",
    "idempotency_keys",
    "model_versions",
    "outcome_adjudications",
    "outcome_reports",
    "outcome_requests",
    "outcome_resolutions",
    "prediction_episodes",
    "prediction_outputs",
    "professional_accreditations",
    "question_presentations",
    "recommendation_feedback",
    "recommendation_instances",
    "recommendation_reviews",
    "recommendation_set_versions",
    "recommendation_sets",
    "schema_migrations",
    "source_mappings",
    "strategies",
    "strategy_citations",
    "strategy_executions",
    "strategy_versions",
    "subject_access_grants",
    "subject_profiles",
    "subjects",
    "target_definition_versions",
    "tenants",
    "training_runs",
    "user_roles",
    "users",
}


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def test_migrations_create_exactly_the_resulting_tables(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "fresh.db"))
    assert database.migrate() == len(discover())
    assert _tables(database.connection) == SPEC_TABLES
    database.close()


def test_migrations_are_idempotent(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "twice.db"))
    database.migrate()
    assert database.migrate() == 0
    database.close()


def test_a_published_migration_cannot_change(tmp_path) -> None:
    connection = connect(tmp_path / "checksum.db")
    migrate(connection, canonical_timestamp(START))
    connection.execute("UPDATE schema_migrations SET checksum = 'otro' WHERE number = 1")
    with pytest.raises(MigrationError):
        migrate(connection, canonical_timestamp(START))
    connection.close()


def test_foreign_keys_are_enforced(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "fk.db"))
    database.migrate()
    with pytest.raises(sqlite3.IntegrityError), database.write() as connection:
        connection.execute(
            "INSERT INTO subjects(subject_id, tenant_id, display_label, cohort_kind, created_at)"
            " VALUES ('s1', 'missing', 'x', 'demo_fixture', 'now')"
        )
    database.close()


def test_sqlite_blocks_pilot_startup(tmp_path) -> None:
    settings = Settings(mode="pilot", database_url="sqlite:///x", db_path=tmp_path / "p.db")  # type: ignore[arg-type]
    with pytest.raises(BlubathonApiError) as error:
        Database(settings)
    assert error.value.code == "pilot_requires_postgresql"


def test_wal_and_busy_timeout_are_active(db) -> None:
    assert db.connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert db.connection.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
