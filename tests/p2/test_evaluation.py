"""Lectura de reportes de evaluación (SPEC 14; INV-33, INV-34)."""

from __future__ import annotations

import pytest

from apps.api.store.json_columns import dump
from tools.seed import ids

MODEL_VERSION = "synthetic-reference-mock-0.2.1"


@pytest.fixture
def published_report(db):
    with db.write() as connection:
        connection.execute(
            "INSERT INTO dataset_snapshots(dataset_snapshot_id, tenant_id, data_origin,"
            " target_definition_version, cutoff_at, episode_ids, observation_ids,"
            " outcome_ids, consent_ids, subject_ids, content_sha256, created_at)"
            " VALUES ('ds-1', ?, 'synthetic', ?, '2026-08-25T12:00:00.000Z', '[]', '[]',"
            " '[]', '[]', '[]', 'sha-dataset', '2026-08-25T12:00:00.000Z')",
            (ids.TENANT_A, ids.TARGET_DEMO_FIXTURE),
        )
        connection.execute(
            "INSERT INTO model_versions(model_version, tenant_id, training_run_id, track_id,"
            " training_data_origin, intended_use, state, artifact_sha256, created_at,"
            " state_changed_at) VALUES (?, ?, NULL, 'synthetic_reference_v021', 'synthetic',"
            " 'simulation_only', 'validated_offline', 'sha-artifact',"
            " '2026-08-25T12:00:00.000Z', '2026-08-25T12:00:00.000Z')",
            (MODEL_VERSION, ids.TENANT_A),
        )
        connection.execute(
            "INSERT INTO evaluation_reports(evaluation_report_id, tenant_id, model_version,"
            " dataset_snapshot_id, protocol_version, target_definition_version, data_origin,"
            " status, metrics, abstention_by_reason, limitations_es, dataset_sha256,"
            " published_at, created_at)"
            " VALUES ('00000000-0000-4000-8000-000000000901', ?, ?, 'ds-1',"
            " 'eval-protocol-1', ?, 'synthetic', 'published', ?, ?, ?, 'sha-dataset',"
            " '2026-08-25T12:00:00.000Z', '2026-08-25T12:00:00.000Z')",
            (
                ids.TENANT_A,
                MODEL_VERSION,
                ids.TARGET_DEMO_FIXTURE,
                dump(
                    [
                        {"name": "brier_score", "estimability": "estimable", "value": 0.21},
                        {
                            "name": "auc_roc",
                            "estimability": "not_estimable",
                            "reason": "single_class",
                        },
                        {
                            "name": "alert_budget_recall",
                            "estimability": "not_estimable",
                            "reason": "no_decision_policy",
                        },
                    ]
                ),
                dump({"insufficient_verified_outcomes": 1.0}),
                dump(
                    [
                        "Métricas de simulación: no demuestran rendimiento clínico.",
                        "Un solo grupo de sujetos sintéticos.",
                    ]
                ),
            ),
        )
    return MODEL_VERSION


def test_evaluator_reads_a_published_report(evaluator, published_report) -> None:
    body = evaluator.get(f"/api/v1/evaluation/{published_report}").json()
    assert body["data_origin"] == "synthetic"
    assert body["simulation_only"] is True
    assert body["dataset_sha256"] == "sha-dataset"
    assert body["model_version"] == published_report
    assert body["limitations_es"]


def test_a_metric_without_support_is_not_estimable_not_zero(evaluator, published_report) -> None:
    """SPEC 14.3: una métrica sin soporte devuelve `not_estimable`."""
    body = evaluator.get(f"/api/v1/evaluation/{published_report}").json()
    by_name = {metric["name"]: metric for metric in body["metrics"]}
    assert by_name["auc_roc"]["estimability"] == "not_estimable"
    assert by_name["auc_roc"]["value"] is None
    assert by_name["alert_budget_recall"]["reason"] == "no_decision_policy"


def test_a_caregiver_cannot_read_an_evaluation(caregiver, published_report) -> None:
    response = caregiver.get(f"/api/v1/evaluation/{published_report}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "role_not_allowed"


def test_an_unpublished_model_version_is_404(evaluator, published_report) -> None:
    response = evaluator.get("/api/v1/evaluation/no-existe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "evaluation_not_found"
