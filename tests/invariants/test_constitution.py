"""One test per non-negotiable rule of SPEC section 0.

These are not coverage. Each one exists so that a specific rule cannot be broken
without the suite going red, and each is named after the rule it guards.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from ml.engine.decision import abstention_reasons, build_risk_response, confidence_label, risk_band
from ml.engine.model import split_by_child
from ml.engine.pipeline import PointInTimeFeatures, assess_risk, merge_today_values
from ml.errors import ContractViolationError
from ml.features import build_feature_matrix, compute_icd
from ml.spec_constants import (
    BAND_AMBER,
    BAND_RED,
    MODEL_INPUT_FIELDS,
    PROVENANCE_FIELDS,
    RANDOM_SEED,
)
from ml.voi import build_form, compute_voi, known_answers
from packages.shared import VARIABLE_LABELS_ES, VARIABLE_PROMPTS_ES, DailyLog
from tests.conftest import last_date

pytestmark = pytest.mark.filterwarnings("ignore")


def test_s0_1_the_llm_never_computes_risk(calm_history, ensemble):
    """Rule 1: the number comes from the deterministic engine, never from text."""
    import ml.narrative.llm as llm_module
    import ml.narrative.template as template_module

    sources = [
        Path(module.__file__).read_text(encoding="utf-8")
        for module in (llm_module, template_module)
    ]
    for text in sources:
        assert "predict" not in text
        assert "RiskEnsemble" not in text
        assert "risk_band(" not in text


def test_s0_2_no_temporal_leakage(calm_history, ensemble):
    """Rule 2: nothing dated after the cut-off can move the prediction."""
    as_of = last_date(calm_history) - timedelta(days=1)
    truncated = [log for log in calm_history if date.fromisoformat(log["date"]) <= as_of]
    future = [log for log in calm_history if date.fromisoformat(log["date"]) > as_of]
    assert future, "fixture must contain days after the cut-off for this test to mean anything"

    child_id = calm_history[0]["child_id"]
    with_future = assess_risk(ensemble, calm_history, child_id, as_of)
    without_future = assess_risk(ensemble, truncated, child_id, as_of)
    assert with_future.probability == without_future.probability


def test_s0_3_canonical_names_are_english_snake_case():
    """Rule 3: code, database and API speak snake_case English."""
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for field_name in PROVENANCE_FIELDS:
        assert pattern.fullmatch(field_name), field_name


def test_s0_3_user_facing_text_is_spanish():
    """Rule 3: everything a person reads is Spanish, and lives in one place."""
    accented = re.compile(r"[áéíóúñ¿¡]")
    assert any(accented.search(text) for text in VARIABLE_PROMPTS_ES.values())
    assert all(prompt.strip() for prompt in VARIABLE_PROMPTS_ES.values())
    assert set(VARIABLE_LABELS_ES) == set(VARIABLE_PROMPTS_ES)


def test_s0_4_risk_is_a_probability(calm_history, ensemble):
    """Rule 4: the canonical risk is a probability; the percentage is derived."""
    as_of = last_date(calm_history)
    assessment = assess_risk(ensemble, calm_history, calm_history[0]["child_id"], as_of)
    assert 0.0 <= assessment.probability <= 1.0
    percentage = round(assessment.probability * 100)
    assert isinstance(percentage, int)
    assert 0 <= percentage <= 100


def test_s0_5_the_model_never_receives_an_imputed_value(calm_history, ensemble):
    """Rule 5: LightGBM gets native NaN; imputation lives only inside VoI."""
    matrix = build_feature_matrix(calm_history)
    features = matrix.drop(columns=["child_id", "date"]).apply(lambda column: column.astype(float))
    assert features.isna().to_numpy().any(), "a real history must reach the model with gaps intact"


def test_s0_6_missingness_is_a_feature_never_a_silent_zero(calm_history):
    """Rule 6: every variable carries its own missing flag."""
    matrix = build_feature_matrix(calm_history)
    for variable in MODEL_INPUT_FIELDS:
        assert f"{variable}_missing" in matrix.columns
    absent = matrix[matrix["gi_status"].isna()]
    if not absent.empty:
        assert bool(absent["gi_status_missing"].all())


def test_s0_7_insufficient_data_abstains_instead_of_guessing():
    """Rule 7: 'I do not know yet' is a valid answer, not an error."""
    assert "low_icd" in abstention_reasons(0.30, 0.20, 30)
    assert "wide_interval" in abstention_reasons(0.90, 0.61, 30)
    assert "short_history" in abstention_reasons(0.90, 0.20, 4)
    assert abstention_reasons(0.90, 0.20, 30) == ()


def test_s0_7_abstention_is_http_200(client, abstain_child_id, abstain_history):
    """Rule 7: abstaining is a legitimate answer with a legitimate status code."""
    target = (last_date(abstain_history) + timedelta(days=1)).isoformat()
    response = client.get("/api/v1/predict", params={"child_id": abstain_child_id, "date": target})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["risk"] is None
    assert body["requested_variables"], "abstaining must say what would help"


def test_s0_8_every_prediction_carries_confidence_and_icd(client, calm_child_id, calm_history):
    """Rule 8: a risk without confidence is never shown."""
    target = (last_date(calm_history) + timedelta(days=1)).isoformat()
    body = client.get("/api/v1/predict", params={"child_id": calm_child_id, "date": target}).json()
    assert "icd" in body
    if body["status"] == "ok":
        assert body["confidence"] in {"alta", "media", "baja"}
    else:
        assert body["confidence"] is None


def test_s0_9_determinism(calm_history, ensemble, population_prior, scorer_factory):
    """Rule 9: seed 42 everywhere means two runs agree exactly."""
    as_of = last_date(calm_history)
    scorer, _ = scorer_factory(calm_history, as_of)
    first = compute_voi(calm_history, as_of, scorer, population_prior)
    second = compute_voi(calm_history, as_of, scorer, population_prior)
    assert [entry["variable"] for entry in first] == [entry["variable"] for entry in second]
    assert [entry["voi"] for entry in first] == [entry["voi"] for entry in second]


def test_s0_10_splits_never_share_a_child():
    """Rule 10: a child is entirely in train, or validation, or test."""
    children = np.array([f"child-{index:03d}" for index in range(120)])
    split = split_by_child(children, seed=RANDOM_SEED)
    assert not (split.train & split.validation)
    assert not (split.train & split.test)
    assert not (split.validation & split.test)
    assert split_by_child(children, seed=RANDOM_SEED) == split


def test_s0_11_language_is_affirmative_and_non_diagnostic():
    """Rule 11: Faro talks about dysregulation and supports, never diagnoses."""
    forbidden = ("diagnóstic", "conducta problema", "trastorno de conducta", "peligro", "patolog")
    from ml.spec_constants import STRATEGIES

    corpus = [*VARIABLE_PROMPTS_ES.values(), *VARIABLE_LABELS_ES.values(), *STRATEGIES.values()]
    for text in corpus:
        lowered = text.lower()
        for term in forbidden:
            assert term not in lowered, f"{term!r} appears in {text!r}"


def test_s0_12_an_untouched_suggestion_is_not_data():
    """Rule 12: a value nobody touched does not exist."""
    with pytest.raises(ValueError):
        DailyLog.model_validate(
            {
                "log_id": "10000000-0000-4000-8000-000000000001",
                "child_id": "10000000-0000-4000-8000-000000000000",
                "date": "2026-08-20",
                "source": "home",
                "sleep_hours": 8.0,
                "capture_method": "form",
                "field_provenance": {"sleep_hours": "assumed_stable"},
                "created_at": "2026-08-20T22:00:00Z",
            }
        )


def test_s0_13_the_form_orders_but_never_hides(calm_history, population_prior, scorer_factory):
    """Rule 13: highlighted plus tail covers every missing variable."""
    as_of = last_date(calm_history)
    scorer, _ = scorer_factory(calm_history, as_of)
    form = build_form(
        calm_history, as_of, calm_history[0]["child_id"], 0.8, scorer, population_prior
    )
    shown = {item["variable"] for item in form["highlighted"]} | {
        item["variable"] for item in form["tail"]
    }
    answered = known_answers(calm_history, as_of)
    missing = {variable for variable in VARIABLE_PROMPTS_ES if answered.get(variable) is None}
    assert shown == missing


def test_s2_5_assumed_stable_never_assigns_a_value():
    """SPEC 2.5: 'nothing new happened' adds coverage, never a number."""
    log = DailyLog.model_validate(
        {
            "log_id": "10000000-0000-4000-8000-000000000002",
            "child_id": "10000000-0000-4000-8000-000000000000",
            "date": "2026-08-20",
            "source": "home",
            "capture_method": "form",
            "field_provenance": {"gi_status": "assumed_stable"},
            "created_at": "2026-08-20T22:00:00Z",
        }
    )
    assert log.gi_status is None
    assert log.field_provenance["gi_status"] == "assumed_stable"


@pytest.mark.parametrize(
    ("probability", "expected"),
    [(0.1499, "verde"), (BAND_AMBER, "ambar"), (0.3499, "ambar"), (BAND_RED, "rojo")],
)
def test_s4_band_edges(probability, expected):
    """SPEC 4: the classic off-by-one that makes you look bad live."""
    assert risk_band(probability) == expected


def test_s5_3_confidence_table():
    """SPEC 5.3: confidence combines data quality with interval width."""
    assert confidence_label(0.70, 0.25) == "alta"
    assert confidence_label(0.70, 0.26) == "media"
    assert confidence_label(0.45, 0.45) == "media"
    assert confidence_label(0.44, 0.45) == "baja"


def test_s6_abstention_response_is_well_formed():
    """SPEC 6: abstaining still returns a valid contract object."""
    response = build_risk_response(
        child_id="10000000-0000-4000-8000-000000000000",
        prediction_date=date(2026, 8, 21),
        probability=0.5,
        interval=(0.1, 0.9),
        icd=0.20,
        history_days=3,
        requested_variables=[
            {"variable": "gi_status", "prompt_es": VARIABLE_PROMPTS_ES["gi_status"], "voi": 0.1}
        ],
    )
    assert response.status == "insufficient_data"
    assert response.risk is None and response.confidence is None
    assert response.requested_variables


def test_merge_today_values_never_invents(calm_history):
    """SPEC rule 0.6 at the merge step: an unanswered field stays absent."""
    as_of = last_date(calm_history)
    merged = merge_today_values(calm_history, as_of, MODEL_INPUT_FIELDS)
    assert all(value is not None for value in merged.values())


def test_point_in_time_features_match_the_full_matrix(calm_history):
    """The incremental feature path must equal the batch one, or VoI lies."""
    as_of = last_date(calm_history)
    child_id = calm_history[0]["child_id"]
    context = PointInTimeFeatures(calm_history, child_id, as_of)
    matrix = build_feature_matrix(calm_history)
    reference = matrix[matrix["date"] == str(as_of)][context.feature_names].astype(float)
    incremental = context.base_row().to_numpy()
    assert np.allclose(incremental, reference.to_numpy(), equal_nan=True)


def test_quality_index_stays_within_bounds(calm_history):
    """SPEC 5.1: every component and the product live in the unit interval."""
    metrics = compute_icd(calm_history, last_date(calm_history))
    for value in metrics.values():
        assert 0.0 <= value <= 1.0


def test_unmapped_bluba_value_is_refused():
    """An unknown category must fail loudly rather than become a silent null."""
    from ml.adapters.bluba import build_bluba_logs

    with pytest.raises(ContractViolationError):
        build_bluba_logs(
            [{"id_caso": "PAC-001", "fecha": "2026-07-01", "calidad_sueno": "Regular"}]
        )


def test_s0_5_the_risk_path_never_reaches_the_sampler(monkeypatch, calm_history, ensemble):
    """Rule 5: scoring must not touch the imputation code at all.

    Structural, not behavioural: if a future refactor routes a prediction
    through the sampler, this fails even when the numbers still look fine.
    """
    import ml.voi.sampling as sampling

    def forbidden(*args, **kwargs):
        raise AssertionError("the risk path called the value-of-information sampler")

    monkeypatch.setattr(sampling, "sample_values", forbidden)
    assess_risk(ensemble, calm_history, calm_history[0]["child_id"], last_date(calm_history))


def test_s0_6_the_store_never_turns_an_absent_field_into_zero(db_conn):
    """Rule 6: a field nobody answered comes back as None, not 0."""
    from apps.api.store import get_history, insert_log

    insert_log(
        db_conn,
        {
            "child_id": "10000000-0000-4000-8000-000000000000",
            "date": "2026-08-20",
            "source": "home",
            "sleep_hours": 7.5,
            "field_provenance": {"sleep_hours": "observed"},
        },
    )
    stored = get_history(db_conn, "10000000-0000-4000-8000-000000000000")[0]
    assert stored["sleep_hours"] == 7.5
    assert stored["gi_status"] is None
    assert stored["dysregulation_events"] is None


def test_s0_6_a_null_crisis_never_becomes_false(db_conn):
    """SPEC 14.1: crisis_occurred is nullable, and null is not 'no crisis'."""
    from apps.api.store import get_history, insert_log

    insert_log(
        db_conn,
        {
            "child_id": "10000000-0000-4000-8000-000000000001",
            "date": "2026-08-20",
            "source": "school",
            "crisis_occurred": None,
        },
    )
    stored = get_history(db_conn, "10000000-0000-4000-8000-000000000001")[0]
    assert stored["crisis_occurred"] is None


def test_s2_5_the_store_refuses_a_provenance_conflict(db_conn):
    """Defence in depth: the database rejects it even without pydantic."""
    from apps.api.store import insert_log

    with pytest.raises(ContractViolationError):
        insert_log(
            db_conn,
            {
                "child_id": "10000000-0000-4000-8000-000000000002",
                "date": "2026-08-20",
                "source": "home",
                "gi_status": 3,
                "field_provenance": {"gi_status": "assumed_stable"},
            },
        )
