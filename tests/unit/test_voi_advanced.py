"""TAREAS 2.3 — VoI avanzado: degradación por antigüedad, prior, recálculo
secuencial, sugerencias (§7.2, §7.3, §7.6)."""

from ml.voi.compute import compute_voi, merge_today_known, suggestion_for, voi_for_variable
from ml.voi.sampling import sample_values, uses_prior


def _history_with_last_seen(variable: str, days_ago: int, base_date: str = "2026-08-20"):
    """Construye un historial donde `variable` fue vista por última vez hace
    `days_ago` días, con >=5 observaciones (evita el prior poblacional)."""
    from datetime import date, timedelta

    d0 = date.fromisoformat(base_date)
    history = []
    last_seen = d0 - timedelta(days=days_ago)
    # >=10 observaciones históricas antes de `last_seen` (para superar
    # VOI_PRIOR_MIN_HISTORY_DAYS=10 y no caer al prior poblacional),
    # separadas por días, con valores variados para que MAD > 0.
    values = [4, 5, 3, 4, 5, 4, 3, 5, 4, 3]
    for i, v in enumerate(values):
        d = last_seen - timedelta(days=(len(values) - i))
        history.append(
            {
                "date": d.isoformat(),
                "child_id": "c1",
                "source": "home",
                variable: v,
                "field_provenance": {variable: "observed"},
            }
        )
    history.append(
        {
            "date": last_seen.isoformat(),
            "child_id": "c1",
            "source": "home",
            variable: 4,
            "field_provenance": {variable: "observed"},
        }
    )
    return history


def test_sigma_crece_con_dias_desde_observacion():
    history_d0 = _history_with_last_seen("gi_status", days_ago=0)
    history_d8 = _history_with_last_seen("gi_status", days_ago=8)
    as_of = "2026-08-20"

    assert not uses_prior(history_d0, "gi_status", as_of)
    assert not uses_prior(history_d8, "gi_status", as_of)

    known = {"sleep_hours": 8.0, "night_awakenings": 0, "routine_changes": False, "alertness": 3}
    voi_d0 = voi_for_variable(history_d0, "gi_status", as_of, known)
    voi_d8 = voi_for_variable(history_d8, "gi_status", as_of, known)
    assert voi_d8 > voi_d0


def test_cold_start_usa_prior_poblacional():
    # Un solo día de historia -> < 10 días -> prior poblacional (§7.2, §8.4).
    history = [
        {
            "date": "2026-08-20",
            "child_id": "c1",
            "source": "home",
            "gi_status": 4,
            "field_provenance": {"gi_status": "observed"},
        }
    ]
    assert uses_prior(history, "gi_status", "2026-08-20") is True
    samples = sample_values(history, "gi_status", "2026-08-20")
    assert len(samples) == 20
    assert all(1 <= s <= 5 for s in samples)


def test_muestras_clipeadas_y_tipo_correcto():
    history = _history_with_last_seen("gi_status", days_ago=10)
    samples = sample_values(history, "gi_status", "2026-08-20")
    assert all(isinstance(s, int) for s in samples)
    assert all(1 <= s <= 5 for s in samples)

    from datetime import date, timedelta

    d0 = date.fromisoformat("2026-08-20")
    sleep_values = [7.0, 8.5, 6.0, 9.0, 7.5, 15.9]  # última muy alta, cerca del tope legal
    history_sleep = [
        {
            "date": (d0 - timedelta(days=len(sleep_values) - i)).isoformat(),
            "child_id": "c1",
            "source": "home",
            "sleep_hours": v,
            "field_provenance": {"sleep_hours": "observed"},
        }
        for i, v in enumerate(sleep_values)
    ]
    samples_sleep = sample_values(history_sleep, "sleep_hours", "2026-08-20")
    assert all(isinstance(s, float) for s in samples_sleep)
    assert all(0.0 <= s <= 16.0 for s in samples_sleep)  # clip al rango legal §2.1


def test_recalculo_secuencial_cambia_el_ranking(high_risk_history):
    as_of = "2026-08-05"
    history = [log for log in high_risk_history if log["date"] <= as_of]
    known = merge_today_known(history, as_of)
    known.pop("sleep_hours", None)
    known.pop("gi_status", None)

    ranking_before = compute_voi(history, as_of, today_known=known)
    top_variable = ranking_before[0]["variable"]

    # Respondo la primera pregunta (con un valor extremo) y recalculo.
    answered = dict(known)
    answered[top_variable] = 16.0 if top_variable == "sleep_hours" else 5
    ranking_after = compute_voi(history, as_of, today_known=answered)

    assert top_variable not in {r["variable"] for r in ranking_after}
    assert ranking_before != ranking_after


def test_sugerencia_requiere_al_menos_5_observaciones():
    history_pocas = _history_with_last_seen("gi_status", days_ago=0)[:3]
    suggestion, _label = suggestion_for(history_pocas, "gi_status", "2026-08-20")
    assert suggestion is None

    history_suficientes = _history_with_last_seen("gi_status", days_ago=0)
    suggestion, label = suggestion_for(history_suficientes, "gi_status", "2026-08-20")
    assert suggestion is not None
    assert label is not None  # gi_status es ordinal -> tiene ancla verbal
