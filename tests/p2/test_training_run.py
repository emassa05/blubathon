"""El entrenamiento offline escribe linaje contra una base migrada de verdad."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ml.prediction.challenger import ChallengerRow
from tools.seed import ids
from tools.train import run as run_module
from tools.train.dataset import TrainingDataset
from tools.train.run import train

TENANT = ids.TENANT_A
TARGET = ids.TARGET_DEMO_FIXTURE


def _train(db, **kwargs):
    with db.write() as connection:
        return train(connection, tenant_id=TENANT, target_definition_version=TARGET, **kwargs)


@pytest.fixture
def trainable(monkeypatch):
    """Un conjunto mínimo que sí entrena, para llegar a las cuatro escrituras.

    El seed de la demo no tiene desenlaces resueltos suficientes, así que sin
    esto el camino en que se publica un modelo no se ejercitaría nunca.
    """

    subjects = [UUID(ids.SUBJECT_ANA), UUID(ids.SUBJECT_BETO)]
    rows = tuple(
        ChallengerRow(
            subject_id=subjects[index % 2],
            p_base=0.1,
            sleep_deviation=0.4 if index % 3 == 0 else -0.2,
            regulation_deviation=0.3 if index % 3 == 0 else -0.1,
            label=1 if index % 3 == 0 else 0,
        )
        for index in range(24)
    )
    dataset = TrainingDataset(
        rows=rows,
        episode_ids=tuple(f"episode-{index}" for index in range(len(rows))),
        observation_ids=("observation-1",),
        outcome_ids=tuple(f"outcome-{index}" for index in range(len(rows))),
        consent_ids=("consent-1",),
        subject_ids=tuple(str(subject) for subject in subjects),
        cutoff_at=datetime(2026, 7, 31, 23, 0, tzinfo=UTC),
        skipped_without_baseline=5,
        skipped_without_predictors=2,
    )
    monkeypatch.setattr(run_module, "build_dataset", lambda *args, **kwargs: dataset)
    return dataset


def test_a_run_that_produces_no_model_is_still_recorded(db) -> None:
    """El intento fallido es el que hay que poder mostrar.

    Cuando alguien pregunta por qué no hay predicción, la respuesta tiene que
    estar escrita en algún lado y no depender de que alguien se acuerde.
    """

    report = _train(db)

    with db.write() as connection:
        runs = connection.execute(
            "SELECT status, reason, code_reference FROM training_runs WHERE tenant_id = ?",
            (TENANT,),
        ).fetchall()
        snapshots = connection.execute(
            "SELECT COUNT(*) FROM dataset_snapshots WHERE tenant_id = ?", (TENANT,)
        ).fetchone()[0]

    assert len(runs) == 1
    assert snapshots == 1
    assert runs[0]["status"] in {"completed", "not_trainable"}
    if not report.published:
        assert runs[0]["reason"] is not None


def test_a_run_that_produces_no_model_publishes_no_model_version(db) -> None:
    report = _train(db)

    assert not report.published
    assert report.reason == "not_trainable_single_class"
    with db.write() as connection:
        versions = connection.execute(
            "SELECT COUNT(*) FROM model_versions WHERE tenant_id = ?", (TENANT,)
        ).fetchone()[0]
        reports = connection.execute(
            "SELECT COUNT(*) FROM evaluation_reports WHERE tenant_id = ?", (TENANT,)
        ).fetchone()[0]

    assert (versions, reports) == (0, 0)


def test_the_snapshot_records_the_cutoff_and_a_fingerprint(db) -> None:
    _train(db)

    with db.write() as connection:
        snapshot = connection.execute(
            "SELECT * FROM dataset_snapshots WHERE tenant_id = ?", (TENANT,)
        ).fetchone()

    assert snapshot["data_origin"] == "real"
    assert snapshot["target_definition_version"] == TARGET
    assert len(snapshot["content_sha256"]) == 64
    for column in ("episode_ids", "observation_ids", "outcome_ids", "subject_ids"):
        assert isinstance(json.loads(snapshot[column]), list)


def test_a_dry_run_writes_nothing(db) -> None:
    _train(db, dry_run=True)

    with db.write() as connection:
        for table in ("dataset_snapshots", "training_runs", "model_versions"):
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = ?", (TENANT,)
            ).fetchone()[0]
            assert count == 0, table


def test_a_published_model_lands_in_shadow_and_never_in_production(db, trainable) -> None:
    """No hay promoción automática: el salto a expuesto es decisión humana."""

    report = _train(db)

    assert report.published
    with db.write() as connection:
        version = connection.execute(
            "SELECT * FROM model_versions WHERE tenant_id = ?", (TENANT,)
        ).fetchone()
        evaluation = connection.execute(
            "SELECT * FROM evaluation_reports WHERE model_version = ?",
            (report.model_version,),
        ).fetchone()

    # El estado no se toca: publicar sigue sin promover nada, y el salto de
    # `shadow` a `shadow_evaluated` sigue siendo decisión humana.
    assert version["state"] == "shadow"
    # El uso declarado sí: el track es operativo desde que su cifra se muestra,
    # y la versión del modelo tiene que decir lo mismo que el track.
    assert version["intended_use"] == "operational_support"
    assert version["training_run_id"] == report.training_run_id
    assert evaluation["dataset_snapshot_id"] == report.dataset_snapshot_id
    assert "sombra" in evaluation["limitations_es"]


def test_the_evaluation_report_carries_its_metrics_and_its_caveats(db, trainable) -> None:
    """La métrica y su letra chica viajan juntas o la métrica se lee sola."""

    report = _train(db)

    with db.write() as connection:
        evaluation = connection.execute(
            "SELECT * FROM evaluation_reports WHERE model_version = ?",
            (report.model_version,),
        ).fetchone()

    metrics = json.loads(evaluation["metrics"])
    assert metrics["n_rows"] == len(trainable.rows)
    assert metrics["brier_out_of_fold"] is not None
    assert metrics["brier_baseline_in_sample"] is not None
    assert json.loads(evaluation["abstentions"]) == {
        "episodes_without_personal_baseline": 5,
        "episodes_without_both_predictors": 2,
    }
    assert evaluation["dataset_sha256"] == trainable.content_sha256
    assert evaluation["published_at"] is None


def test_the_adapter_finds_the_published_shadow_version(db, trainable) -> None:
    """Sin esta fila el challenger responde `model_state_not_shadow`."""

    from apps.api.store import history
    from packages.shared.enums import TrackId

    report = _train(db)

    with db.write() as connection:
        found = history.shadow_model_version(
            connection,
            tenant_id=TENANT,
            track_id=TrackId.REAL_LOGIT_CHALLENGER_V1.value,
        )

    assert found is not None
    assert found["model_version"] == report.model_version
