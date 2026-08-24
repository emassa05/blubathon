"""TAREAS 2.8 — Métricas y ablaciones (§13). Funciones puras, arreglos
sintéticos."""

from ml.eval.ablations import adherence_probability, stale_variable_miss_rate
from ml.eval.metrics import (
    alert_budget_recall,
    auc_roc,
    average_precision,
    baseline_always_base_rate,
    baseline_yesterday_dysregulation,
    brier_score,
    decision_coverage,
    expected_calibration_error,
    fairness_sex,
)


def test_average_precision_perfecto_vs_azar():
    y_true = [0, 0, 1, 1]
    y_perfect = [0.1, 0.2, 0.8, 0.9]
    y_random = [0.5, 0.5, 0.5, 0.5]
    assert average_precision(y_true, y_perfect) == 1.0
    assert average_precision(y_true, y_random) < 1.0


def test_auc_roc_perfecto():
    y_true = [0, 0, 1, 1]
    y_score = [0.1, 0.2, 0.8, 0.9]
    assert auc_roc(y_true, y_score) == 1.0


def test_brier_score_prediccion_perfecta_es_cero():
    assert brier_score([1, 0, 1], [1.0, 0.0, 1.0]) == 0.0
    assert brier_score([1, 0], [0.0, 1.0]) == 1.0


def test_ece_10_bins_calibracion_perfecta():
    y_true = [1] * 10 + [0] * 90
    y_prob = [0.1] * 100  # calibración perfecta: 10% de positivos, p=0.1
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    assert ece < 1e-9


def test_alert_budget_recall_es_curva_por_nino():
    y_true = [1, 0, 0, 1, 0]
    y_score = [0.9, 0.1, 0.2, 0.8, 0.05]
    child_ids = ["a", "a", "a", "b", "b"]
    result = alert_budget_recall(y_true, y_score, child_ids, budget_per_child=1)
    assert result["at_budget"] == 1.0  # top-1 de cada niño captura ambos positivos
    assert 1 in result["curve"]


def test_decision_coverage():
    assert decision_coverage(["ok", "ok", "insufficient_data", "ok"]) == 0.75
    assert decision_coverage([]) == 0.0


def test_fairness_sex_honesto_con_diferencia():
    y_true = [1, 0, 1, 0, 1, 0]
    y_score = [0.9, 0.1, 0.9, 0.1, 0.2, 0.8]  # F perfecto, M invertido
    sex = ["F", "F", "F", "F", "M", "M"]
    out = fairness_sex(y_true, y_score, sex)
    assert out["F"]["auc_pr"] > out["M"]["auc_pr"]


def test_baselines_obligatorios():
    y_true = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0]
    base_rate_scores = baseline_always_base_rate(y_true)
    assert all(s == 0.2 for s in base_rate_scores)

    dysregulation_yesterday = [True, False, False, True, False, False, False, False, False, False]
    yest_scores = baseline_yesterday_dysregulation(dysregulation_yesterday)
    assert yest_scores == [1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_adherencia_valores_del_spec():
    assert abs(adherence_probability(2) - 0.860) < 1e-9
    assert abs(adherence_probability(5) - 0.725) < 1e-9
    assert adherence_probability(15) == 0.30  # clip


def test_stale_variable_miss_rate():
    days = [
        {"delta": 3, "asked": False},  # miss
        {"delta": 1, "asked": False},  # no cambió lo suficiente
        {"delta": 3, "asked": True},  # se preguntó -> no es miss
    ]
    assert abs(stale_variable_miss_rate(days) - 1 / 3) < 1e-9
    assert stale_variable_miss_rate([]) == 0.0
