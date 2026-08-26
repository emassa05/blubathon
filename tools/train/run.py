"""Entrenamiento offline del challenger, con su linaje escrito en la base.

Cuatro tablas encadenadas, en este orden y por esta razón:

- `dataset_snapshots` fija sobre qué filas se entrenó. Sin esto, un Brier es un
  número sobre «la base», que cambia cada vez que un tutor registra un día.
- `training_runs` deja el intento, incluso cuando no hay modelo. Un entrenamiento
  que no procede porque hay una sola clase es un resultado, no un no-evento, y es
  el que hay que poder mostrar cuando alguien pregunte por qué no hay predicción.
- `model_versions` publica el artefacto en estado `shadow`. No hay promoción
  automática a producción: el paso de sombra a expuesto es una decisión humana y
  esta herramienta no la toma.
- `evaluation_reports` guarda el Brier fuera de muestra junto a sus limitaciones
  en texto. La métrica y su letra chica viajan juntas o la métrica se lee sola.

La herramienta no decide si el modelo es bueno. Mide, escribe lo que midió y
deja el veredicto a la vista.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from apps.api.canonical import canonical_timestamp
from ml.prediction.challenger import (
    CHALLENGER_PROTOCOL_VERSION,
    ChallengerFit,
    train_challenger,
)
from packages.shared.enums import EstimateKind, IntendedUse, TrackId
from tools.train.dataset import TrainingDataset, build_dataset

DATA_ORIGIN = "real"
MODEL_STATE = "shadow"
REPORT_STATUS = "draft"


@dataclass(frozen=True, slots=True)
class TrainingReport:
    """Lo que pasó, se haya publicado modelo o no."""

    training_run_id: str
    dataset_snapshot_id: str
    status: str
    reason: str | None
    n_rows: int
    n_positive: int
    n_negative: int
    n_subjects: int
    skipped_without_baseline: int
    skipped_without_predictors: int
    model_version: str | None = None
    penalty: float | None = None
    brier_challenger: float | None = None
    brier_baseline: float | None = None
    fit: ChallengerFit | None = None

    @property
    def published(self) -> bool:
        return self.model_version is not None

    @property
    def beats_baseline(self) -> bool | None:
        if self.brier_challenger is None or self.brier_baseline is None:
            return None
        return self.brier_challenger < self.brier_baseline


def train(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    target_definition_version: str,
    cutoff_at: datetime | None = None,
    dry_run: bool = False,
) -> TrainingReport:
    """Arma el conjunto, entrena, evalúa y deja escrito el linaje."""

    now = datetime.now(UTC)
    dataset = build_dataset(connection, tenant_id=tenant_id, cutoff_at=cutoff_at or now)
    result = train_challenger(dataset.rows)

    snapshot_id = str(uuid4())
    run_id = str(uuid4())
    status = "completed" if result.trainable else "not_trainable"
    reason = None if result.reason is None else result.reason.value

    brier_baseline = _baseline_brier(dataset)
    penalty = None if result.selection is None else result.selection.penalty
    brier = None if result.selection is None else result.selection.brier
    # Separador `-` y no `+`: la etiqueta viaja en el contrato desde que el
    # challenger se expone, y `VersionLabel` solo admite `[a-z0-9._-]`. El `+`
    # de metadatos de build de semver nunca se validó porque nadie la publicaba.
    model_version = f"{result.model_version}-{run_id[:8]}" if result.trainable else None

    report = TrainingReport(
        training_run_id=run_id,
        dataset_snapshot_id=snapshot_id,
        status=status,
        reason=reason,
        n_rows=len(dataset.rows),
        n_positive=dataset.n_positive,
        n_negative=dataset.n_negative,
        n_subjects=len({row.subject_id for row in dataset.rows}),
        skipped_without_baseline=dataset.skipped_without_baseline,
        skipped_without_predictors=dataset.skipped_without_predictors,
        model_version=model_version,
        penalty=penalty,
        brier_challenger=brier,
        brier_baseline=brier_baseline,
        fit=result.fit,
    )
    if dry_run:
        return report

    with connection:
        _write_snapshot(
            connection,
            dataset,
            snapshot_id=snapshot_id,
            tenant_id=tenant_id,
            target_definition_version=target_definition_version,
            now=now,
        )
        _write_run(
            connection,
            snapshot_id=snapshot_id,
            run_id=run_id,
            tenant_id=tenant_id,
            status=status,
            reason=reason,
            now=now,
        )
        if model_version is not None:
            _write_model_version(
                connection,
                run_id=run_id,
                tenant_id=tenant_id,
                model_version=model_version,
                fit=result.fit,
                now=now,
            )
            _write_evaluation(
                connection,
                dataset,
                report=report,
                tenant_id=tenant_id,
                target_definition_version=target_definition_version,
                now=now,
            )
    return report


def _baseline_brier(dataset: TrainingDataset) -> float | None:
    """Brier del baseline sobre las mismas filas, para tener contra qué comparar.

    Es *dentro* de muestra: `p_base` se calculó con los desenlaces previos del
    mismo niño, sin dejar ninguno afuera. Le juega a favor frente al Brier del
    challenger, que es fuera de muestra. La comparación sólo sirve en una
    dirección: si el challenger igual gana, ganó con la cancha inclinada en
    contra; si pierde, no se puede concluir nada.
    """

    if not dataset.rows:
        return None
    return sum((row.p_base - row.label) ** 2 for row in dataset.rows) / len(dataset.rows)


def _code_reference() -> str:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"
    return revision


def _dependency_manifest() -> str:
    return json.dumps(
        {"python": platform.python_version(), "protocol": CHALLENGER_PROTOCOL_VERSION},
        separators=(",", ":"),
        sort_keys=True,
    )


def _protocol_sha256() -> str:
    """Huella del protocolo, no del código: lo que fija qué se prometió medir."""

    return hashlib.sha256(CHALLENGER_PROTOCOL_VERSION.encode("utf-8")).hexdigest()


def _write_snapshot(
    connection: sqlite3.Connection,
    dataset: TrainingDataset,
    *,
    snapshot_id: str,
    tenant_id: str,
    target_definition_version: str,
    now: datetime,
) -> None:
    connection.execute(
        "INSERT INTO dataset_snapshots (dataset_snapshot_id, tenant_id, data_origin,"
        " target_definition_version, cutoff_at, episode_ids, observation_ids, outcome_ids,"
        " consent_ids, subject_ids, content_sha256, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            snapshot_id,
            tenant_id,
            DATA_ORIGIN,
            target_definition_version,
            canonical_timestamp(dataset.cutoff_at),
            json.dumps(list(dataset.episode_ids)),
            json.dumps(list(dataset.observation_ids)),
            json.dumps(list(dataset.outcome_ids)),
            json.dumps(list(dataset.consent_ids)),
            json.dumps(list(dataset.subject_ids)),
            dataset.content_sha256,
            canonical_timestamp(now),
        ),
    )


def _write_run(
    connection: sqlite3.Connection,
    *,
    snapshot_id: str,
    run_id: str,
    tenant_id: str,
    status: str,
    reason: str | None,
    now: datetime,
) -> None:
    connection.execute(
        "INSERT INTO training_runs (training_run_id, tenant_id, dataset_snapshot_id, track_id,"
        " protocol_version, protocol_sha256, status, reason, code_reference,"
        " dependency_manifest, started_at, finished_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            tenant_id,
            snapshot_id,
            TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            CHALLENGER_PROTOCOL_VERSION,
            _protocol_sha256(),
            status,
            reason,
            _code_reference(),
            _dependency_manifest(),
            canonical_timestamp(now),
            canonical_timestamp(datetime.now(UTC)),
        ),
    )


def _write_model_version(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    tenant_id: str,
    model_version: str,
    fit: ChallengerFit | None,
    now: datetime,
) -> None:
    artifact = json.dumps(
        {
            "intercept": None if fit is None else fit.intercept,
            "beta_sleep": None if fit is None else fit.beta_sleep,
            "beta_regulation": None if fit is None else fit.beta_regulation,
            "penalty": None if fit is None else fit.penalty,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    # El artefacto se guarda, no solo su hash: sin los coeficientes el runtime
    # no puede puntuar y el track abstiene aunque haya versión publicada.
    connection.execute(
        "INSERT INTO model_versions (model_version, tenant_id, training_run_id, track_id,"
        " training_data_origin, intended_use, state, artifact_sha256, artifact, created_at,"
        " state_changed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            model_version,
            tenant_id,
            run_id,
            TrackId.REAL_LOGIT_CHALLENGER_V1.value,
            DATA_ORIGIN,
            # El mismo uso que declara el track en `TRACK_INTENDED_USE`.
            IntendedUse.OPERATIONAL_SUPPORT.value,
            MODEL_STATE,
            hashlib.sha256(artifact.encode("utf-8")).hexdigest(),
            artifact,
            canonical_timestamp(now),
            canonical_timestamp(now),
        ),
    )


def _write_evaluation(
    connection: sqlite3.Connection,
    dataset: TrainingDataset,
    *,
    report: TrainingReport,
    tenant_id: str,
    target_definition_version: str,
    now: datetime,
) -> None:
    metrics = {
        "brier_out_of_fold": report.brier_challenger,
        "brier_baseline_in_sample": report.brier_baseline,
        "penalty": report.penalty,
        "n_rows": report.n_rows,
        "n_positive": report.n_positive,
        "n_subjects": report.n_subjects,
        "estimate_kind": EstimateKind.SHADOW_CHALLENGER_SCORE.value,
        "coefficients": {
            "intercept": None if report.fit is None else report.fit.intercept,
            "beta_sleep": None if report.fit is None else report.fit.beta_sleep,
            "beta_regulation": None if report.fit is None else report.fit.beta_regulation,
        },
    }
    abstentions = {
        "episodes_without_personal_baseline": dataset.skipped_without_baseline,
        "episodes_without_both_predictors": dataset.skipped_without_predictors,
    }
    connection.execute(
        "INSERT INTO evaluation_reports (evaluation_report_id, tenant_id, model_version,"
        " dataset_snapshot_id, protocol_version, target_definition_version, data_origin,"
        " status, metrics, abstentions, limitations_es, dataset_sha256, published_at,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid4()),
            tenant_id,
            report.model_version,
            report.dataset_snapshot_id,
            CHALLENGER_PROTOCOL_VERSION,
            target_definition_version,
            DATA_ORIGIN,
            REPORT_STATUS,
            json.dumps(metrics, separators=(",", ":"), sort_keys=True),
            json.dumps(abstentions, separators=(",", ":"), sort_keys=True),
            limitations(report),
            dataset.content_sha256,
            None,
            canonical_timestamp(now),
        ),
    )


def limitations(report: TrainingReport) -> str:
    """La letra chica que viaja pegada a la métrica."""

    parts = [
        f"Entrenado sobre {report.n_rows} episodios de {report.n_subjects} niños,"
        f" con {report.n_positive} crisis observadas.",
        "El Brier del challenger es fuera de muestra dejando un niño afuera; el del"
        " baseline es dentro de muestra, así que la comparación favorece al baseline"
        " y sólo concluye si el challenger igual gana.",
    ]
    if report.penalty is not None and report.fit is not None:
        coefficients = (report.fit.beta_sleep or 0.0, report.fit.beta_regulation or 0.0)
        if max(abs(value) for value in coefficients) < 1e-3:
            parts.append(
                f"La regularización elegida (lambda={report.penalty:g}) dejó los dos"
                " coeficientes en prácticamente cero: la mejora viene del intercepto,"
                " es decir de recalibrar la tasa base, no de los predictores."
            )
    parts.append(
        "Modelo en sombra. No se expone a cuidadores ni a profesionales y no hay"
        " promoción automática a producción."
    )
    return " ".join(parts)
