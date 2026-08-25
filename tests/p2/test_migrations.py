"""Migraciones inmutables, FK activas y bloqueo de SQLite en piloto.

Cubre INV-30 y los criterios de migración de `TAREAS P2.3`.
"""

from __future__ import annotations

import sqlite3

import pytest

from apps.api.canonical import format_timestamp
from apps.api.clock import FrozenClock
from apps.api.errors import FaroApiError
from apps.api.settings import Settings
from apps.api.store.db import Database, connect
from apps.api.store.migrations import MigrationError, discover, migrate
from tests.p2.conftest import START

SPEC_TABLES = {
    "tenants",
    "users",
    "user_roles",
    "professional_accreditations",
    "subjects",
    "subject_profiles",
    "subject_access_grants",
    "consents",
    "form_sessions",
    "default_presentations",
    "question_presentations",
    "field_observations",
    "source_mappings",
    "prediction_episodes",
    "feature_snapshots",
    "prediction_outputs",
    "target_definition_versions",
    "outcome_requests",
    "outcome_reports",
    "outcome_resolutions",
    "outcome_adjudications",
    "document_versions",
    "document_chunks",
    "authoring_build_manifests",
    "authoring_reviews",
    "corpus_versions",
    "strategies",
    "strategy_versions",
    "strategy_citations",
    "recommendation_sets",
    "catalog_versions",
    "recommendation_instances",
    "recommendation_reviews",
    "human_plan_versions",
    "strategy_executions",
    "authoring_requests",
    "authoring_use_authorizations",
    "dataset_snapshots",
    "training_runs",
    "model_versions",
    "evaluation_reports",
    "audit_events",
    "idempotency_keys",
}


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }


def test_migrations_create_every_table_of_spec_12_1(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "fresh.db"))
    assert database.migrate() == len(discover())
    assert _tables(database.connection) >= SPEC_TABLES
    database.close()


def test_migrations_are_idempotent(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "twice.db"))
    database.migrate()
    assert database.migrate() == 0
    database.close()


def test_migrations_run_over_a_fictional_v0_2_database(tmp_path) -> None:
    """TAREAS P2.3: prueba de migración desde una base v0.2 ficticia."""
    path = tmp_path / "legacy.db"
    legacy = connect(path)
    legacy.executescript(
        "CREATE TABLE daily_logs (log_id TEXT PRIMARY KEY, child_id TEXT NOT NULL);"
        "CREATE TABLE feedback (feedback_id TEXT PRIMARY KEY, child_id TEXT NOT NULL);"
        "INSERT INTO daily_logs VALUES ('log-1', 'child-1');"
    )
    legacy.close()

    database = Database(Settings(db_path=path))
    database.migrate()
    tables = _tables(database.connection)
    assert tables >= SPEC_TABLES
    # La historia v0.2 se conserva: la migración no borra lo anterior.
    assert tables >= {"daily_logs", "feedback"}
    rows = database.connection.execute("SELECT COUNT(*) AS n FROM daily_logs").fetchone()
    assert rows["n"] == 1
    database.close()


def test_a_published_migration_cannot_change(tmp_path) -> None:
    path = tmp_path / "checksum.db"
    connection = connect(path)
    migrate(connection, format_timestamp(START))
    connection.execute("UPDATE schema_migrations SET checksum = 'otro' WHERE number = 1")
    with pytest.raises(MigrationError):
        migrate(connection, format_timestamp(START))
    connection.close()


def test_foreign_keys_are_enforced(tmp_path) -> None:
    database = Database(Settings(db_path=tmp_path / "fk.db"))
    database.migrate()
    with pytest.raises(sqlite3.IntegrityError), database.write() as connection:
        connection.execute(
            "INSERT INTO subjects(subject_id, tenant_id, display_label, cohort_kind,"
            " created_at) VALUES ('s1', 'tenant-inexistente', 'x', 'demo_fixture', 'now')"
        )
    database.close()


def test_sqlite_blocks_pilot_startup(tmp_path) -> None:
    """INV-30: SQLite en modo piloto bloquea el arranque."""
    settings = Settings(mode="pilot", database_url="sqlite:///x", db_path=tmp_path / "p.db")  # type: ignore[arg-type]
    with pytest.raises(FaroApiError) as error:
        Database(settings)
    assert error.value.code == "pilot_requires_postgresql"


def test_a_real_subject_is_refused_in_demo_mode(tmp_path, caregiver, db) -> None:
    """SPEC 12.3: un sujeto `real_subject` en modo demo bloquea la operación."""
    with db.write() as connection:
        connection.execute(
            "UPDATE subjects SET cohort_kind = 'real_subject' WHERE subject_id = ?",
            ("00000000-0000-4000-8000-000000000101",),
        )
    response = caregiver.post(
        "/api/v1/form-sessions",
        {
            "subject_id": "00000000-0000-4000-8000-000000000101",
            "source": "home",
            "session_kind": "caregiver_daily",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cohort_not_allowed"
    assert tmp_path


def test_wal_and_busy_timeout_are_active(db) -> None:
    journal = db.connection.execute("PRAGMA journal_mode").fetchone()[0]
    timeout = db.connection.execute("PRAGMA busy_timeout").fetchone()[0]
    assert journal.lower() == "wal"
    assert timeout >= 5000
    assert isinstance(FrozenClock, type)


def test_overlapping_primary_episodes_fail_closed(caregiver, db) -> None:
    """SPEC 4.2: la decisión se serializa por (tenant_id, subject_id).

    En SQLite la serialización la da `BEGIN IMMEDIATE`; este test comprueba la
    segunda línea de defensa, que es la comprobación de solape dentro de la
    transacción y el índice único sobre el inicio de la ventana.
    """
    import pytest

    from apps.api.errors import FaroApiError
    from apps.api.store import episodes
    from tests.p2.test_episodes_and_outcomes import complete_session
    from tools.seed import ids

    result = complete_session(caregiver)
    episode = episodes.episode(db.connection, result["prediction_episode_id"])
    assert episode is not None

    with pytest.raises(FaroApiError) as error, db.write() as connection:
        episodes.create_primary_episode(
            connection,
            episodes.NewEpisode(
                tenant_id=ids.TENANT_A,
                subject_id=ids.SUBJECT_ANA,
                form_session_id=episode["form_session_id"],
                as_of_at="2026-08-25T18:00:00.000Z",
                target_start_at="2026-08-25T18:00:00.000Z",
                target_end_at="2026-08-26T18:00:00.000Z",
                capture_deadline_at="2026-08-27T18:00:00.000Z",
                target_definition_version=ids.TARGET_DEMO_FIXTURE,
                profile_version="profile-1",
                care_mode="home_and_therapy",
                input_data_origin="synthetic",
                created_at="2026-08-25T18:00:00.000Z",
            ),
        )
    assert error.value.status_code == 409
    total = db.connection.execute(
        "SELECT COUNT(*) AS n FROM prediction_episodes WHERE role = 'primary'"
    ).fetchone()["n"]
    assert total == 1
