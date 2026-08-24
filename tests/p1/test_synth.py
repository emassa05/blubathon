from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.spec_constants import (
    CATEGORICAL_FIELDS,
    FIELD_RANGES,
    HIGH_WEIGHT_FIELDS,
    MEDICATION_ADHERENCE_VALUES,
    PROVENANCE_FIELDS,
    RANDOM_SEED,
    SYNTH_BASE_RATE_MAX,
    SYNTH_BASE_RATE_MIN,
    SYNTH_COEFFICIENTS,
    SYNTH_DAYS,
    SYNTH_DAYS_PER_WEEK,
    SYNTH_FEMALE_SIGNAL_FACTOR,
    SYNTH_GENERATOR_VERSION,
    SYNTH_MISSING_BASE,
    SYNTH_MISSING_FORGETFUL_MULTIPLIER,
    SYNTH_MISSING_LOAD_FACTOR,
    SYNTH_MISSING_LOAD_OFFSET,
    SYNTH_MISSING_MAX,
    SYNTH_MISSING_SLEEP_MULTIPLIER,
    SYNTH_N_CHILDREN,
    SYNTH_PERSONAL_BASE_RATE_MAX,
    SYNTH_PERSONAL_BASE_RATE_MIN,
    SYNTH_THERAPY_DAYS_PER_WEEK,
    SYNTH_WEEKEND_START,
)
from ml.synth.generate import (
    SyntheticDataset,
    _missing_probability,
    apply_camouflage,
    generate_synthetic_data,
    write_dataset,
)
from packages.shared import DailyLog


@pytest.fixture(scope="module")
def dataset() -> SyntheticDataset:
    return generate_synthetic_data()


def test_generates_full_population_and_structural_sources(dataset: SyntheticDataset) -> None:
    truth = dataset.ground_truth
    logs = dataset.logs
    assert truth["child_id"].nunique() == SYNTH_N_CHILDREN
    assert len(truth) == SYNTH_N_CHILDREN * SYNTH_DAYS
    assert truth.groupby("child_id")["date"].nunique().eq(SYNTH_DAYS).all()
    assert logs[logs["source"] == "home"].groupby("child_id").size().eq(SYNTH_DAYS).all()

    school_dates = pd.to_datetime(logs.loc[logs["source"] == "school", "date"])
    assert school_dates.dt.weekday.lt(SYNTH_WEEKEND_START).all()
    complete_weeks = SYNTH_DAYS // SYNTH_DAYS_PER_WEEK
    therapy_counts = logs[logs["source"] == "therapy"].groupby("child_id").size()
    assert therapy_counts.between(
        complete_weeks * SYNTH_THERAPY_DAYS_PER_WEEK,
        (complete_weeks + 1) * SYNTH_THERAPY_DAYS_PER_WEEK,
    ).all()


def test_observed_base_rate_matches_target(dataset: SyntheticDataset) -> None:
    home = dataset.logs[dataset.logs["source"] == "home"]
    base_rate = home["crisis_occurred"].mean()
    assert SYNTH_BASE_RATE_MIN <= base_rate <= SYNTH_BASE_RATE_MAX


def test_next_day_target_is_aligned_without_leakage(dataset: SyntheticDataset) -> None:
    truth = dataset.ground_truth.sort_values(["child_id", "date"])
    expected_current = truth.groupby("child_id")["crisis_next_day"].shift()
    comparable = expected_current.notna()
    assert (
        truth.loc[comparable, "current_crisis"].astype(bool).to_numpy()
        == expected_current.loc[comparable].astype(bool).to_numpy()
    ).all()
    expected_probability = 1.0 / (1.0 + np.exp(-truth["latent_load"]))
    assert np.allclose(truth["p_crisis_next_day"], expected_probability)
    assert "latent_load" not in dataset.logs.columns


def test_latent_load_reconstructs_from_fixed_equation(dataset: SyntheticDataset) -> None:
    truth = dataset.ground_truth
    coefficient = SYNTH_COEFFICIENTS
    reconstructed = (
        coefficient["intercept"]
        + coefficient["sleep"] * truth["sleep_debt"]
        + coefficient["awakenings"] * truth["awakenings_z"]
        + truth["gi_coefficient"] * truth["gi_burden"]
        + coefficient["routine"] * truth["routine_load"]
        + coefficient["sensory"] * truth["sensory_load"]
        + coefficient["sleep_routine"] * truth["sleep_debt"] * truth["routine_load"]
        + coefficient["gi_sensory"] * truth["gi_burden"] * truth["sensory_load"]
        + coefficient["medication"] * truth["medication_missed"].astype(float)
        + coefficient["carryover"] * truth["previous_load"]
        + truth["susceptibility"]
        + truth["innovation"]
    )
    assert np.allclose(truth["latent_load"], reconstructed)


def test_categorical_fields_only_hold_declared_values(dataset: SyntheticDataset) -> None:
    """A nominal field has a vocabulary, not a range (SPEC 2.1 field 16)."""
    values = set(dataset.logs["medication_adherence"].dropna().unique())
    assert values
    assert values <= set(MEDICATION_ADHERENCE_VALUES)


def test_high_weight_variables_stay_in_legal_ranges(dataset: SyntheticDataset) -> None:
    logs = dataset.logs
    for variable in HIGH_WEIGHT_FIELDS - set(CATEGORICAL_FIELDS):
        values = logs[variable].dropna().astype(float)
        lower, upper = FIELD_RANGES[variable]
        assert not values.empty
        assert values.between(lower, upper).all()


def test_missingness_formula_and_nmar_gradient(dataset: SyntheticDataset) -> None:
    standard = min(
        SYNTH_MISSING_MAX,
        SYNTH_MISSING_BASE
        + SYNTH_MISSING_LOAD_FACTOR / (1.0 + math.exp(-(0.0 - SYNTH_MISSING_LOAD_OFFSET))),
    )
    assert _missing_probability(0.0, "wake_state") == pytest.approx(standard)
    assert _missing_probability(0.0, "gi_status") == pytest.approx(
        min(SYNTH_MISSING_MAX, standard * SYNTH_MISSING_FORGETFUL_MULTIPLIER)
    )
    assert _missing_probability(0.0, "sleep_hours") == pytest.approx(
        standard * SYNTH_MISSING_SLEEP_MULTIPLIER
    )

    home = dataset.logs[dataset.logs["source"] == "home"].copy()
    home["missing_fraction"] = home[list(HIGH_WEIGHT_FIELDS)].isna().mean(axis=1)
    truth = dataset.ground_truth[["child_id", "date", "latent_load"]]
    merged = home.merge(truth, on=["child_id", "date"], validate="one_to_one")
    low_load = merged[merged["latent_load"] <= merged["latent_load"].quantile(0.25)]
    high_load = merged[merged["latent_load"] >= merged["latent_load"].quantile(0.75)]
    assert high_load["missing_fraction"].mean() > low_load["missing_fraction"].mean()


def test_profile_ratios_and_semantics_match_spec(dataset: SyntheticDataset) -> None:
    profiles = dataset.ground_truth.drop_duplicates("child_id")
    assert (profiles["support_level"] == "low").mean() == pytest.approx(0.60)
    assert (profiles["verbal"] == "verbal").mean() == pytest.approx(0.70)
    assert profiles["chronic_gi"].mean() == pytest.approx(0.30)
    assert (profiles["sex"] == "F").mean() == pytest.approx(0.50)
    assert (
        profiles["base_rate_i"]
        .between(SYNTH_PERSONAL_BASE_RATE_MIN, SYNTH_PERSONAL_BASE_RATE_MAX)
        .all()
    )
    grouped = profiles.groupby("support_level")
    assert grouped["susceptibility"].mean()["high"] > grouped["susceptibility"].mean()["low"]
    assert grouped["noise_std"].mean()["high"] > grouped["noise_std"].mean()["low"]


def test_female_camouflage_attenuates_generated_signals(dataset: SyntheticDataset) -> None:
    truth = dataset.ground_truth
    female = truth[truth["sex"] == "F"]
    male = truth[truth["sex"] == "M"]
    assert np.allclose(
        female["dysregulation_signal_observed"],
        female["dysregulation_signal_unmasked"] * SYNTH_FEMALE_SIGNAL_FACTOR,
    )
    assert np.allclose(male["dysregulation_signal_observed"], male["dysregulation_signal_unmasked"])
    female_tag_ratio = (
        female["behavior_tag_count_observed"].sum() / female["behavior_tag_count_true"].sum()
    )
    male_tag_ratio = (
        male["behavior_tag_count_observed"].sum() / male["behavior_tag_count_true"].sum()
    )
    assert female_tag_ratio == pytest.approx(SYNTH_FEMALE_SIGNAL_FACTOR, abs=0.02)
    assert male_tag_ratio == pytest.approx(1.0)
    assert apply_camouflage(4.0, "F") == pytest.approx(4.0 * SYNTH_FEMALE_SIGNAL_FACTOR)


def test_provenance_matches_presence(dataset: SyntheticDataset) -> None:
    for record in dataset.logs.sample(n=500, random_state=RANDOM_SEED).to_dict("records"):
        provenance = record["field_provenance"]
        assert set(provenance) == set(PROVENANCE_FIELDS)
        for field_name in PROVENANCE_FIELDS:
            value = record[field_name]
            is_missing = value is None or value is pd.NA
            if field_name == "observed_behavior_tags":
                is_missing = value == []
            expected = "unknown" if is_missing else "observed"
            assert provenance[field_name] == expected


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_two_independent_runs_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_dataset(generate_synthetic_data(n_children=8, days=21), first)
    write_dataset(generate_synthetic_data(n_children=8, days=21), second)
    for filename in ("logs.parquet", "ground_truth.parquet", "manifest.json"):
        assert _sha256(first / filename) == _sha256(second / filename)


def _normalize_parquet_value(value: object) -> object:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def test_parquet_logs_validate_against_daily_log(tmp_path: Path) -> None:
    output = tmp_path / "schema"
    write_dataset(generate_synthetic_data(n_children=3, days=7), output)
    records = pd.read_parquet(output / "logs.parquet").to_dict("records")
    for record in records:
        normalized = {key: _normalize_parquet_value(value) for key, value in record.items()}
        DailyLog.model_validate(normalized)


def test_manifest_is_complete_and_contains_no_local_path(dataset: SyntheticDataset) -> None:
    manifest = dataset.manifest
    assert manifest["generator_version"] == SYNTH_GENERATOR_VERSION
    assert {
        "population",
        "causal_model",
        "profiles",
        "observation_model",
        "missingness",
        "sources",
    }.issubset(manifest)
    assert "path" not in str(manifest).lower()
    manifest["causal_model"]["coefficients"]["sleep"] = -1
    assert SYNTH_COEFFICIENTS["sleep"] == 0.90
