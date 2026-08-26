"""El entrenamiento offline deja linaje completo, incluso cuando no hay modelo."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ml.prediction.challenger import ChallengerRow
from tools.train.dataset import TrainingDataset
from tools.train.run import TrainingReport, _baseline_brier, limitations


def _dataset(rows: tuple[ChallengerRow, ...] = ()) -> TrainingDataset:
    return TrainingDataset(
        rows=rows,
        episode_ids=("e1", "e2"),
        observation_ids=("o2", "o1"),
        outcome_ids=("r1",),
        consent_ids=("c1",),
        subject_ids=("s1",),
        cutoff_at=datetime(2026, 7, 31, tzinfo=UTC),
        skipped_without_baseline=3,
        skipped_without_predictors=1,
    )


def _row(*, p_base: float, label: int) -> ChallengerRow:
    from uuid import UUID

    return ChallengerRow(
        subject_id=UUID("00000000-0000-4000-8000-000000000101"),
        p_base=p_base,
        sleep_deviation=0.0,
        regulation_deviation=0.0,
        label=label,
    )


def _report(**overrides: object) -> TrainingReport:
    fields: dict[str, object] = {
        "training_run_id": "run",
        "dataset_snapshot_id": "snap",
        "status": "completed",
        "reason": None,
        "n_rows": 82,
        "n_positive": 5,
        "n_negative": 77,
        "n_subjects": 4,
        "skipped_without_baseline": 20,
        "skipped_without_predictors": 0,
    }
    fields.update(overrides)
    return TrainingReport(**fields)  # type: ignore[arg-type]


def test_the_dataset_fingerprint_ignores_the_order_the_ids_came_out_in() -> None:
    # Dos corridas sobre los mismos datos pueden leerlos en distinto orden; si
    # eso cambiara la huella, dos evaluaciones idénticas parecerían distintas.
    first = _dataset()
    second = TrainingDataset(
        rows=(),
        episode_ids=("e2", "e1"),
        observation_ids=("o1", "o2"),
        outcome_ids=("r1",),
        consent_ids=("c1",),
        subject_ids=("s1",),
        cutoff_at=first.cutoff_at,
        skipped_without_baseline=3,
        skipped_without_predictors=1,
    )

    assert first.content_sha256 == second.content_sha256


def test_a_different_dataset_gets_a_different_fingerprint() -> None:
    other = TrainingDataset(
        rows=(),
        episode_ids=("e1", "e2", "e3"),
        observation_ids=("o1", "o2"),
        outcome_ids=("r1",),
        consent_ids=("c1",),
        subject_ids=("s1",),
        cutoff_at=datetime(2026, 7, 31, tzinfo=UTC),
        skipped_without_baseline=3,
        skipped_without_predictors=1,
    )

    assert _dataset().content_sha256 != other.content_sha256


def test_the_baseline_brier_is_none_without_rows() -> None:
    assert _baseline_brier(_dataset()) is None


def test_the_baseline_brier_scores_the_base_rate_against_the_outcome() -> None:
    dataset = _dataset(rows=(_row(p_base=0.2, label=0), _row(p_base=0.5, label=1)))

    assert _baseline_brier(dataset) == pytest.approx((0.04 + 0.25) / 2)


def test_limitations_say_the_comparison_favours_the_baseline() -> None:
    text = limitations(_report())

    assert "fuera de muestra" in text
    assert "dentro de muestra" in text
    assert "sombra" in text


def test_limitations_call_out_coefficients_crushed_to_zero() -> None:
    from ml.prediction.challenger import ChallengerFit

    fit = ChallengerFit(
        converged=True,
        intercept=-1.01,
        beta_sleep=2.3e-05,
        beta_regulation=4.8e-05,
        penalty=100.0,
    )

    text = limitations(_report(penalty=100.0, fit=fit))

    assert "recalibrar la tasa base" in text


def test_limitations_stay_quiet_when_the_coefficients_carry_weight() -> None:
    from ml.prediction.challenger import ChallengerFit

    fit = ChallengerFit(
        converged=True, intercept=-1.0, beta_sleep=0.47, beta_regulation=0.22, penalty=0.01
    )

    assert "recalibrar la tasa base" not in limitations(_report(penalty=0.01, fit=fit))


def test_beats_baseline_is_unknown_without_both_scores() -> None:
    assert _report(brier_challenger=0.05).beats_baseline is None


def test_beats_baseline_compares_the_two_scores() -> None:
    assert _report(brier_challenger=0.059, brier_baseline=0.070).beats_baseline is True
    assert _report(brier_challenger=0.080, brier_baseline=0.070).beats_baseline is False
