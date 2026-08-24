"""TAREAS 2.2 — VoI base (§7.1)."""

from ml.spec_constants import RANDOM_SEED, VOI_K
from ml.voi.compute import compute_voi, merge_today_known, voi_for_variable


def test_k20_reproducible_con_seed_42(high_risk_history):
    assert RANDOM_SEED == 42
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history, as_of)
    v1 = voi_for_variable(history, "sleep_hours", as_of, known, k=VOI_K)
    v2 = voi_for_variable(history, "sleep_hours", as_of, known, k=VOI_K)
    assert v1 == v2


def test_variables_presentes_no_aparecen_en_ranking(calm_history):
    as_of = "2026-08-10"
    history = [log for log in calm_history if log["date"] <= as_of]
    # el día calmo tiene TODAS las variables presentes -> ranking vacío
    ranking = compute_voi(history, as_of)
    assert ranking == []


def test_variable_que_no_mueve_p_da_voi_cero(high_risk_history):
    """`sleep_quality` no es input de `predict_baseline` (no forma parte del
    latente causal §8.1): imputarla no debería mover `p` en absoluto."""
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history, as_of)
    known.pop("sleep_quality", None)
    voi = voi_for_variable(history, "sleep_quality", as_of, known)
    assert voi == 0.0


def test_variable_que_mueve_mucho_da_voi_alto(high_risk_history):
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history, as_of)
    known.pop("sleep_quality", None)
    known.pop("sleep_hours", None)
    voi_sleep = voi_for_variable(history, "sleep_hours", as_of, known)
    voi_quality = voi_for_variable(history, "sleep_quality", as_of, known)
    assert voi_sleep > voi_quality
