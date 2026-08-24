"""TAREAS 2.4 — Formulario adaptativo y salvaguardas (§7.4, §7.5)."""

from datetime import date, timedelta

from ml.spec_constants import IMPORTANCE_WEIGHTS, STALENESS_CEILING_DAYS
from ml.voi.form import (
    build_form,
    detect_anomaly,
    exploration_triggered,
    resolve_filter_no,
    staleness_candidates,
)


def _flat_history(days: int, as_of: str, missing: set[str] = frozenset()):
    """Historial con TODAS las variables en un valor central estable,
    excepto las de `missing`, durante `days` días terminando en `as_of`."""
    d0 = date.fromisoformat(as_of)
    values = {
        "sleep_hours": 8.0,
        "sleep_quality": 4,
        "night_awakenings": 1,
        "wake_state": 4,
        "morning_support_need": 2,
        "gi_status": 4,
        "routine_changes": False,
        "alertness": 3,
        "dysregulation_events": 1,
        "activity_participation": 4,
        "social_interactions": 4,
        "eating_status": 4,
        "food_changes": False,
        "relevant_event_flag": False,
    }
    history = []
    for i in range(days):
        d = d0 - timedelta(days=days - 1 - i)
        entry = {"date": d.isoformat(), "child_id": "c1", "source": "home", "field_provenance": {}}
        for field, v in values.items():
            if field in missing and d.isoformat() == as_of:
                continue
            entry[field] = v
            entry["field_provenance"][field] = "observed"
        history.append(entry)
    return history


def test_build_form_shape_incluye_bloque_0():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of, missing={"gi_status", "routine_changes"})
    form = build_form(history, as_of, child_id="c1", icd=0.9)
    assert set(form) >= {
        "child_id",
        "date",
        "highlighted",
        "filter_question_es",
        "tail",
        "closing_question_es",
        "closing_target_date",
    }
    assert len(form["highlighted"]) == 2  # ICD >= 0.5 -> tamaño default


def test_highlighted_size_3_con_icd_bajo():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of, missing={"gi_status", "routine_changes", "alertness"})
    form = build_form(history, as_of, child_id="c1", icd=0.4)
    assert len(form["highlighted"]) == 3


def test_closing_question_presente_si_no_se_reporto_target():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of)  # el día anterior nunca reportó crisis_occurred
    form = build_form(history, as_of, child_id="c1", icd=0.9)
    assert form["closing_question_es"] is not None
    assert form["closing_target_date"] == "2026-08-19"


def test_closing_question_null_si_ya_se_reporto_target():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of)
    history.append(
        {
            "date": "2026-08-19",
            "child_id": "c1",
            "source": "home",
            "crisis_occurred": False,
            "field_provenance": {"crisis_occurred": "observed"},
        }
    )
    form = build_form(history, as_of, child_id="c1", icd=0.9)
    assert form["closing_question_es"] is None
    assert form["closing_target_date"] is None


def test_techo_de_antiguedad_desplaza_la_de_menor_voi():
    as_of = "2026-08-20"
    # gi_status y routine_changes faltan HOY y llevan 7 días sin observarse.
    missing = {"gi_status", "routine_changes"}
    history = _flat_history(20, as_of, missing=missing)
    # fuerzo d_v >= 7 quitando esas variables de los últimos 7 días.
    cutoff = date.fromisoformat(as_of) - timedelta(days=STALENESS_CEILING_DAYS - 1)
    for log in history:
        if date.fromisoformat(log["date"]) >= cutoff:
            for v in missing:
                log.pop(v, None)
                log.get("field_provenance", {}).pop(v, None)

    missing_vars = missing
    stale = staleness_candidates(history, as_of, missing_vars)
    assert set(stale) == missing

    form = build_form(history, as_of, child_id="c1", icd=0.9)
    highlighted_vars = {item["variable"] for item in form["highlighted"]}
    assert missing & highlighted_vars  # al menos una entró por techo
    assert len(form["highlighted"]) == 2  # el bloque NO crece


def test_techo_desempate_w_v_luego_dv_luego_alfabetico():
    as_of = "2026-08-20"
    missing = {"gi_status", "routine_changes"}  # w_v: 0.7 y 0.7 (empate) -> alfabético
    history = _flat_history(20, as_of, missing=missing)
    cutoff = date.fromisoformat(as_of) - timedelta(days=STALENESS_CEILING_DAYS - 1)
    for log in history:
        if date.fromisoformat(log["date"]) >= cutoff:
            for v in missing:
                log.pop(v, None)
                log.get("field_provenance", {}).pop(v, None)
    assert IMPORTANCE_WEIGHTS["gi_status"] == IMPORTANCE_WEIGHTS["routine_changes"]
    stale = staleness_candidates(history, as_of, missing)
    assert stale[0] == "gi_status"  # alfabético entre empatados


def test_cuota_de_exploracion_determinista():
    # Busco una fecha/child_id donde el hash caiga en 0 mod 7.
    found = None
    for day_offset in range(0, 30):
        d = (date.fromisoformat("2026-08-01") + timedelta(days=day_offset)).isoformat()
        if exploration_triggered("child-x", d):
            found = d
            break
    assert found is not None
    assert exploration_triggered("child-x", found) is True  # reproducible
    assert exploration_triggered("child-x", found) == exploration_triggered("child-x", found)


def test_precedencia_techo_gana_sobre_exploracion():
    as_of = "2026-08-20"
    missing = {"gi_status", "routine_changes"}
    history = _flat_history(20, as_of, missing=missing)
    cutoff = date.fromisoformat(as_of) - timedelta(days=STALENESS_CEILING_DAYS - 1)
    for log in history:
        if date.fromisoformat(log["date"]) >= cutoff:
            for v in missing:
                log.pop(v, None)
                log.get("field_provenance", {}).pop(v, None)

    # Busco un child_id donde exploración SÍ dispare ese día, para probar
    # que aun así manda el techo.
    child_id = next(cid for cid in (f"child-{i}" for i in range(50)) if exploration_triggered(cid, as_of))
    form = build_form(history, as_of, child_id=child_id, icd=0.9)
    reasons = {item["variable"]: item["reason"] for item in form["highlighted"]}
    assert "staleness" in reasons.values()
    assert "exploration" not in reasons.values()


def test_gatillo_por_anomalia():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of)
    # gi_status normal = 4 (MAD chico); hoy respondo 1 -> z fuerte.
    today_known = {"gi_status": 1}
    assert detect_anomaly(history, as_of, today_known) is True
    assert detect_anomaly(history, as_of, {"gi_status": 4}) is False


def test_filtro_no_asigna_assumed_stable_sin_valor_salvo_anomalia():
    as_of = "2026-08-20"
    history = _flat_history(15, as_of)
    tail_vars = ["gi_status", "routine_changes"]

    result_normal = resolve_filter_no(history, as_of, tail_vars, today_known={"alertness": 3})
    assert result_normal == {v: "assumed_stable" for v in tail_vars}

    result_anomaly = resolve_filter_no(history, as_of, tail_vars, today_known={"gi_status": 1})
    assert result_anomaly == {}  # el gatillo por anomalía despliega la cola igual
