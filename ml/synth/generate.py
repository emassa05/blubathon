"""Causal synthetic population defined by SPEC section 8."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd

from ml.spec_constants import (
    BASELINE_ALERTNESS_OPTIMAL,
    BASELINE_AWAKENINGS_CENTER,
    BASELINE_AWAKENINGS_SCALE,
    BEHAVIOR_TAGS,
    BOOLEAN_FIELDS,
    DYSREGULATION_EVENTS_MAX,
    DYSREGULATION_EVENTS_MIN,
    MEDICATION_ADHERENCE_VALUES,
    NIGHT_AWAKENINGS_MAX,
    NIGHT_AWAKENINGS_MIN,
    ORDINAL_FIELDS,
    ORDINAL_MAX,
    ORDINAL_MIN,
    PROVENANCE_FIELDS,
    RANDOM_SEED,
    SOURCE_ALLOWED_FIELDS,
    SPEC_VERSION,
    SYNTH_ALERTNESS_NOISE_STD,
    SYNTH_AWAKENINGS_BASE,
    SYNTH_AWAKENINGS_LOAD_FACTOR,
    SYNTH_CAUSAL_ITERATIONS,
    SYNTH_CHRONIC_GI_PROBABILITY,
    SYNTH_COEFFICIENTS,
    SYNTH_DAYS,
    SYNTH_DAYS_PER_WEEK,
    SYNTH_DYSREGULATION_LOAD_FACTOR,
    SYNTH_DYSREGULATION_NOISE_MEAN,
    SYNTH_DYSREGULATION_NOISE_STD,
    SYNTH_EVENT_PROBABILITY_MAX,
    SYNTH_EVENT_PROBABILITY_MIN,
    SYNTH_FEMALE_PROBABILITY,
    SYNTH_FEMALE_SIGNAL_FACTOR,
    SYNTH_GENERATOR_VERSION,
    SYNTH_GI_BURDEN_WEIGHTS,
    SYNTH_GI_CHRONIC_PENALTY,
    SYNTH_GI_NOISE_STD,
    SYNTH_HIGH_SUPPORT_NOISE_MULTIPLIER,
    SYNTH_MEDICATED_PROBABILITY,
    SYNTH_MEDICATION_MISS_PROBABILITY,
    SYNTH_MISSING_BASE,
    SYNTH_MISSING_FORGETFUL_MULTIPLIER,
    SYNTH_MISSING_LOAD_FACTOR,
    SYNTH_MISSING_LOAD_OFFSET,
    SYNTH_MISSING_MAX,
    SYNTH_MISSING_SLEEP_MULTIPLIER,
    SYNTH_N_CHILDREN,
    SYNTH_NOISE_STD,
    SYNTH_NONVERBAL_GI_MULTIPLIER,
    SYNTH_PARTICIPATION_NOISE_STD,
    SYNTH_PERSONAL_BASE_RATE_MAX,
    SYNTH_PERSONAL_BASE_RATE_MIN,
    SYNTH_ROUTINE_LOAD_WEIGHTS,
    SYNTH_SLEEP_DEBT_WEIGHTS,
    SYNTH_SLEEP_LOAD_DIVISOR,
    SYNTH_SLEEP_LOAD_FACTOR,
    SYNTH_SLEEP_NEED_MAX,
    SYNTH_SLEEP_NEED_MEAN,
    SYNTH_SLEEP_NEED_MIN,
    SYNTH_SLEEP_NEED_STD,
    SYNTH_SLEEP_NOISE_STD,
    SYNTH_SLEEP_OBSERVED_MAX,
    SYNTH_SLEEP_OBSERVED_MIN,
    SYNTH_START_DATE,
    SYNTH_STATE_NOISE_STD,
    SYNTH_SUPPORT_LOW_PROBABILITY,
    SYNTH_SUSCEPTIBILITY_STD,
    SYNTH_THERAPY_WEEKDAYS,
    SYNTH_VERBAL_PROBABILITY,
    SYNTH_WEEKEND_START,
)
from packages.shared import DailyLog


@dataclass(frozen=True)
class SyntheticDataset:
    logs: pd.DataFrame
    ground_truth: pd.DataFrame
    manifest: dict[str, Any]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def _clip_ordinal(value: float) -> int:
    return int(np.clip(round(value), ORDINAL_MIN, ORDINAL_MAX))


def _poisson_quantile(quantile: float, rate: float) -> int:
    """Invert a Poisson CDF while reusing one draw during causal fixed-point iterations."""
    probability = math.exp(-rate)
    cumulative = probability
    value = NIGHT_AWAKENINGS_MIN
    while quantile > cumulative and value < NIGHT_AWAKENINGS_MAX:
        value += 1
        probability *= rate / value
        cumulative += probability
    return value


def _deterministic_uuid(*parts: object) -> str:
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).digest()
    return str(UUID(bytes=digest[:16], version=4))


def _exact_binary_profile(
    rng: np.random.Generator,
    size: int,
    positive_probability: float,
    positive: str,
    negative: str,
) -> np.ndarray:
    positive_count = round(size * positive_probability)
    values = np.array([positive] * positive_count + [negative] * (size - positive_count))
    return rng.permutation(values)


def apply_camouflage(signal: float, sex: str) -> float:
    """Attenuate observable signals for female profiles without changing latent load."""
    if sex == "F":
        return signal * SYNTH_FEMALE_SIGNAL_FACTOR
    return signal


def _profile_table(
    rng: np.random.Generator,
    n_children: int,
    seed: int,
    coefficients: Mapping[str, float] = SYNTH_COEFFICIENTS,
) -> pd.DataFrame:
    susceptibility = rng.normal(0.0, SYNTH_SUSCEPTIBILITY_STD, n_children)
    susceptibility_min = _logit(SYNTH_PERSONAL_BASE_RATE_MIN) - coefficients["intercept"]
    susceptibility_max = _logit(SYNTH_PERSONAL_BASE_RATE_MAX) - coefficients["intercept"]
    susceptibility = np.clip(susceptibility, susceptibility_min, susceptibility_max)

    low_support_count = round(n_children * SYNTH_SUPPORT_LOW_PROBABILITY)
    support_level = np.full(n_children, "high", dtype=object)
    support_level[np.argsort(susceptibility)[:low_support_count]] = "low"
    high_fraction = 1.0 - SYNTH_SUPPORT_LOW_PROBABILITY
    low_noise_multiplier = math.sqrt(
        (1.0 - high_fraction * SYNTH_HIGH_SUPPORT_NOISE_MULTIPLIER**2)
        / SYNTH_SUPPORT_LOW_PROBABILITY
    )
    noise_std = np.where(
        support_level == "high",
        SYNTH_NOISE_STD * SYNTH_HIGH_SUPPORT_NOISE_MULTIPLIER,
        SYNTH_NOISE_STD * low_noise_multiplier,
    )
    verbal = _exact_binary_profile(
        rng,
        n_children,
        SYNTH_VERBAL_PROBABILITY,
        "verbal",
        "nonverbal",
    )
    chronic_gi = _exact_binary_profile(
        rng,
        n_children,
        SYNTH_CHRONIC_GI_PROBABILITY,
        "yes",
        "no",
    )
    sex = _exact_binary_profile(rng, n_children, SYNTH_FEMALE_PROBABILITY, "F", "M")
    medicated = _exact_binary_profile(rng, n_children, SYNTH_MEDICATED_PROBABILITY, "yes", "no")
    sleep_need = np.clip(
        rng.normal(SYNTH_SLEEP_NEED_MEAN, SYNTH_SLEEP_NEED_STD, n_children),
        SYNTH_SLEEP_NEED_MIN,
        SYNTH_SLEEP_NEED_MAX,
    )
    return pd.DataFrame(
        {
            "child_index": np.arange(n_children),
            "child_id": [_deterministic_uuid(seed, "child", index) for index in range(n_children)],
            "support_level": support_level,
            "verbal": verbal,
            "chronic_gi": chronic_gi == "yes",
            "medicated": medicated == "yes",
            "sex": sex,
            "sleep_need": sleep_need,
            "susceptibility": susceptibility,
            "noise_std": noise_std,
            "base_rate_i": [
                _sigmoid(coefficients["intercept"] + value) for value in susceptibility
            ],
        }
    )


def _weighted_history(values: list[float], current: float, weights: tuple[float, ...]) -> float:
    sequence = [current, *reversed(values)]
    return sum(
        weight * sequence[index] for index, weight in enumerate(weights) if index < len(sequence)
    )


def _sleep_quality(sleep_hours: float, sleep_need: float, awakenings: int) -> int:
    relative_sleep = sleep_hours / sleep_need
    score = ORDINAL_MAX * relative_sleep - awakenings / SYNTH_AWAKENINGS_LOAD_FACTOR
    return _clip_ordinal(score)


def _event_probability(previous_load: float) -> float:
    return float(
        np.clip(
            SYNTH_EVENT_PROBABILITY_MIN
            + (SYNTH_EVENT_PROBABILITY_MAX - SYNTH_EVENT_PROBABILITY_MIN) * _sigmoid(previous_load),
            0.0,
            1.0,
        )
    )


def _missing_probability(latent_load: float, field_name: str) -> float:
    probability = SYNTH_MISSING_BASE + SYNTH_MISSING_LOAD_FACTOR * _sigmoid(
        latent_load - SYNTH_MISSING_LOAD_OFFSET
    )
    if field_name in {"gi_status", "social_interactions", "night_awakenings"}:
        probability *= SYNTH_MISSING_FORGETFUL_MULTIPLIER
    elif field_name in {"sleep_hours", "sleep_quality"}:
        probability *= SYNTH_MISSING_SLEEP_MULTIPLIER
    return float(np.clip(probability, 0.0, SYNTH_MISSING_MAX))


def _causal_components(
    *,
    candidate_load: float,
    profile: pd.Series,
    sleep_deficits: list[float],
    gi_burdens: list[float],
    routine_events: list[float],
    routine_changes: bool,
    relevant_event_flag: bool,
    sleep_noise: float,
    gi_noise: float,
    alertness_noise: float,
    awakening_quantile: float,
    medication_missed: bool = False,
) -> dict[str, float | int]:
    sleep_hours = float(
        np.clip(
            profile.sleep_need
            - SYNTH_SLEEP_LOAD_FACTOR * max(0.0, candidate_load / SYNTH_SLEEP_LOAD_DIVISOR)
            + sleep_noise,
            SYNTH_SLEEP_OBSERVED_MIN,
            SYNTH_SLEEP_OBSERVED_MAX,
        )
    )
    awakening_rate = SYNTH_AWAKENINGS_BASE + SYNTH_AWAKENINGS_LOAD_FACTOR * max(0.0, candidate_load)
    night_awakenings = int(
        np.clip(
            _poisson_quantile(awakening_quantile, awakening_rate),
            NIGHT_AWAKENINGS_MIN,
            NIGHT_AWAKENINGS_MAX,
        )
    )
    gi_penalty = SYNTH_GI_CHRONIC_PENALTY if profile.chronic_gi else 0.0
    gi_status = _clip_ordinal(ORDINAL_MAX - gi_penalty - max(0.0, candidate_load) + gi_noise)
    alertness = _clip_ordinal(
        BASELINE_ALERTNESS_OPTIMAL + max(0.0, candidate_load) + alertness_noise
    )
    sleep_deficit = max(0.0, profile.sleep_need - sleep_hours) / profile.sleep_need
    gi_burden_current = (ORDINAL_MAX - gi_status) / (ORDINAL_MAX - ORDINAL_MIN)
    sleep_debt = _weighted_history(sleep_deficits, sleep_deficit, SYNTH_SLEEP_DEBT_WEIGHTS)
    gi_burden = _weighted_history(gi_burdens, gi_burden_current, SYNTH_GI_BURDEN_WEIGHTS)
    routine_load = _weighted_history(
        routine_events, float(routine_changes), SYNTH_ROUTINE_LOAD_WEIGHTS
    )
    sensory_load = min(
        1.0,
        abs(alertness - BASELINE_ALERTNESS_OPTIMAL) / (ORDINAL_MAX - BASELINE_ALERTNESS_OPTIMAL)
        + float(relevant_event_flag),
    )
    return {
        "medication_missed": float(medication_missed),
        "sleep_hours": sleep_hours,
        "sleep_deficit": sleep_deficit,
        "sleep_debt": sleep_debt,
        "night_awakenings": night_awakenings,
        "awakenings_z": (night_awakenings - BASELINE_AWAKENINGS_CENTER) / BASELINE_AWAKENINGS_SCALE,
        "gi_status": gi_status,
        "gi_burden_current": gi_burden_current,
        "gi_burden": gi_burden,
        "routine_load": routine_load,
        "alertness": alertness,
        "sensory_load": sensory_load,
    }


def _latent_load(
    *,
    components: dict[str, float | int],
    profile: pd.Series,
    previous_load: float,
    innovation: float,
    coefficients: Mapping[str, float] = SYNTH_COEFFICIENTS,
) -> float:
    coefficient = coefficients
    gi_coefficient = coefficient["gi"] * (
        SYNTH_NONVERBAL_GI_MULTIPLIER if profile.verbal == "nonverbal" else 1.0
    )
    return float(
        coefficient["intercept"]
        + coefficient["sleep"] * components["sleep_debt"]
        + coefficient["awakenings"] * components["awakenings_z"]
        + gi_coefficient * components["gi_burden"]
        + coefficient["routine"] * components["routine_load"]
        + coefficient["sensory"] * components["sensory_load"]
        + coefficient["sleep_routine"] * components["sleep_debt"] * components["routine_load"]
        + coefficient["gi_sensory"] * components["gi_burden"] * components["sensory_load"]
        + coefficient["medication"] * float(components.get("medication_missed", 0.0))
        + coefficient["carryover"] * previous_load
        + profile.susceptibility
        + innovation
    )


def _observed_fields(
    rng: np.random.Generator,
    latent_load: float,
    source: str,
    canonical: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    allowed_fields = SOURCE_ALLOWED_FIELDS[source]
    values: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for field_name in PROVENANCE_FIELDS:
        value = canonical.get(field_name)
        has_value = value is not None and value != []
        is_observed = (
            field_name in allowed_fields
            and has_value
            and rng.random() >= _missing_probability(latent_load, field_name)
        )
        if field_name == "crisis_occurred":
            is_observed = True
        if field_name == "observed_behavior_tags":
            values[field_name] = list(value) if is_observed else []
        else:
            values[field_name] = value if is_observed else None
        provenance[field_name] = "observed" if is_observed else "unknown"
    return values, provenance


def _make_log(
    *,
    rng: np.random.Generator,
    seed: int,
    child_id: str,
    day: date,
    source: str,
    latent_load: float,
    canonical: dict[str, Any],
) -> dict[str, Any]:
    values, provenance = _observed_fields(rng, latent_load, source, canonical)
    created_at = datetime.combine(day, time.max, UTC).replace(microsecond=0)
    record = {
        "log_id": _deterministic_uuid(seed, child_id, day.isoformat(), source),
        "child_id": child_id,
        "date": day.isoformat(),
        "source": source,
        **values,
        "capture_method": "synthetic",
        "field_provenance": provenance,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }
    if provenance["observed_behavior_tags"] == "unknown":
        record.pop("observed_behavior_tags")
    return DailyLog.model_validate(record).model_dump(mode="json")


def _observed_tags(
    rng: np.random.Generator,
    *,
    sex: str,
    dysregulation_events: int,
    alertness: int,
    current_crisis: bool,
    day_index: int,
) -> tuple[list[str], list[str]]:
    if dysregulation_events == DYSREGULATION_EVENTS_MIN:
        true_tags = [BEHAVIOR_TAGS[0]]
    elif alertness > BASELINE_ALERTNESS_OPTIMAL:
        true_tags = [BEHAVIOR_TAGS[1]]
    else:
        true_tags = [BEHAVIOR_TAGS[2]]
    if current_crisis:
        major_tags = BEHAVIOR_TAGS[5:9]
        true_tags.append(major_tags[day_index % len(major_tags)])
    if sex == "F":
        return true_tags, [tag for tag in true_tags if rng.random() < SYNTH_FEMALE_SIGNAL_FACTOR]
    return true_tags, list(true_tags)


def _generate_child(
    *,
    rng: np.random.Generator,
    seed: int,
    profile: pd.Series,
    start_date: date,
    days: int,
    coefficients: Mapping[str, float] = SYNTH_COEFFICIENTS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    previous_load = 0.0
    current_crisis = bool(rng.random() < profile.base_rate_i)
    sleep_deficits: list[float] = []
    gi_burdens: list[float] = []
    routine_events: list[float] = []
    logs: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []

    for day_index in range(days):
        day = start_date + timedelta(days=day_index)
        event_probability = _event_probability(previous_load)
        routine_changes = bool(rng.random() < event_probability)
        food_changes = bool(rng.random() < event_probability)
        relevant_event_flag = bool(rng.random() < event_probability)
        medication_missed = bool(
            profile.medicated and rng.random() < SYNTH_MEDICATION_MISS_PROBABILITY
        )
        medication_adherence = (
            None
            if not profile.medicated
            else MEDICATION_ADHERENCE_VALUES[1]
            if medication_missed
            else MEDICATION_ADHERENCE_VALUES[0]
        )
        if not profile.medicated:
            medication_adherence = MEDICATION_ADHERENCE_VALUES[2]
        sleep_noise = rng.normal(0.0, SYNTH_SLEEP_NOISE_STD)
        gi_noise = rng.normal(0.0, SYNTH_GI_NOISE_STD)
        alertness_noise = rng.normal(0.0, SYNTH_ALERTNESS_NOISE_STD)
        awakening_quantile = rng.random()
        innovation = rng.normal(0.0, profile.noise_std)

        candidate_load = previous_load
        for _ in range(SYNTH_CAUSAL_ITERATIONS):
            components = _causal_components(
                candidate_load=candidate_load,
                profile=profile,
                sleep_deficits=sleep_deficits,
                gi_burdens=gi_burdens,
                routine_events=routine_events,
                routine_changes=routine_changes,
                relevant_event_flag=relevant_event_flag,
                sleep_noise=sleep_noise,
                gi_noise=gi_noise,
                alertness_noise=alertness_noise,
                awakening_quantile=awakening_quantile,
                medication_missed=medication_missed,
            )
            candidate_load = _latent_load(
                components=components,
                profile=profile,
                previous_load=previous_load,
                innovation=innovation,
                coefficients=coefficients,
            )
        components = _causal_components(
            candidate_load=candidate_load,
            profile=profile,
            sleep_deficits=sleep_deficits,
            gi_burdens=gi_burdens,
            routine_events=routine_events,
            routine_changes=routine_changes,
            relevant_event_flag=relevant_event_flag,
            sleep_noise=sleep_noise,
            gi_noise=gi_noise,
            alertness_noise=alertness_noise,
            awakening_quantile=awakening_quantile,
            medication_missed=medication_missed,
        )
        latent_load = _latent_load(
            components=components,
            profile=profile,
            previous_load=previous_load,
            innovation=innovation,
            coefficients=coefficients,
        )
        load_signal = max(0.0, latent_load)
        sleep_quality = _sleep_quality(
            components["sleep_hours"], profile.sleep_need, components["night_awakenings"]
        )
        wake_state = _clip_ordinal(
            ORDINAL_MAX - load_signal + rng.normal(0.0, SYNTH_STATE_NOISE_STD)
        )
        morning_support_need = _clip_ordinal(
            ORDINAL_MIN + load_signal + rng.normal(0.0, SYNTH_STATE_NOISE_STD)
        )
        raw_dysregulation_signal = max(
            0.0,
            load_signal * SYNTH_DYSREGULATION_LOAD_FACTOR
            + rng.normal(SYNTH_DYSREGULATION_NOISE_MEAN, SYNTH_DYSREGULATION_NOISE_STD),
        )
        observed_dysregulation_signal = apply_camouflage(raw_dysregulation_signal, profile.sex)
        dysregulation_events = int(
            np.clip(
                round(observed_dysregulation_signal),
                DYSREGULATION_EVENTS_MIN,
                DYSREGULATION_EVENTS_MAX,
            )
        )
        activity_participation = _clip_ordinal(
            ORDINAL_MAX - load_signal + rng.normal(0.0, SYNTH_PARTICIPATION_NOISE_STD)
        )
        social_interactions = _clip_ordinal(
            ORDINAL_MAX
            - apply_camouflage(load_signal, profile.sex)
            + rng.normal(0.0, SYNTH_PARTICIPATION_NOISE_STD)
        )
        eating_status = _clip_ordinal(
            ORDINAL_MAX - load_signal + rng.normal(0.0, SYNTH_STATE_NOISE_STD)
        )
        true_tags, observed_tags = _observed_tags(
            rng,
            sex=profile.sex,
            dysregulation_events=dysregulation_events,
            alertness=components["alertness"],
            current_crisis=current_crisis,
            day_index=day_index,
        )

        canonical = {
            "sleep_hours": round(components["sleep_hours"], 2),
            "sleep_quality": sleep_quality,
            "night_awakenings": components["night_awakenings"],
            "wake_state": wake_state,
            "morning_support_need": morning_support_need,
            "gi_status": components["gi_status"],
            "medication_adherence": medication_adherence,
            "food_changes": food_changes,
            "routine_changes": routine_changes,
            "observed_behavior_tags": observed_tags,
            "observed_behavior_note": None,
            "alertness": components["alertness"],
            "dysregulation_events": dysregulation_events,
            "activity_participation": activity_participation,
            "social_interactions": social_interactions,
            "eating_status": eating_status,
            "relevant_event_flag": relevant_event_flag,
            "relevant_events_note": None,
            "crisis_occurred": current_crisis,
            "other_notes": None,
        }
        logs.append(
            _make_log(
                rng=rng,
                seed=seed,
                child_id=profile.child_id,
                day=day,
                source="home",
                latent_load=latent_load,
                canonical=canonical,
            )
        )
        if day.weekday() < SYNTH_WEEKEND_START:
            logs.append(
                _make_log(
                    rng=rng,
                    seed=seed,
                    child_id=profile.child_id,
                    day=day,
                    source="school",
                    latent_load=latent_load,
                    canonical=canonical,
                )
            )
        therapy_offset = int(profile.child_id[-1], 16) % SYNTH_DAYS_PER_WEEK
        therapy_weekdays = {
            (weekday + therapy_offset) % SYNTH_DAYS_PER_WEEK for weekday in SYNTH_THERAPY_WEEKDAYS
        }
        if day.weekday() in therapy_weekdays:
            logs.append(
                _make_log(
                    rng=rng,
                    seed=seed,
                    child_id=profile.child_id,
                    day=day,
                    source="therapy",
                    latent_load=latent_load,
                    canonical=canonical,
                )
            )

        next_probability = _sigmoid(latent_load)
        next_crisis = bool(rng.random() < next_probability)
        gi_coefficient = coefficients["gi"] * (
            SYNTH_NONVERBAL_GI_MULTIPLIER if profile.verbal == "nonverbal" else 1.0
        )
        ground_truth.append(
            {
                "child_id": profile.child_id,
                "date": day.isoformat(),
                "latent_load": latent_load,
                "previous_load": previous_load,
                "innovation": innovation,
                "sleep_debt": components["sleep_debt"],
                "awakenings_z": components["awakenings_z"],
                "gi_burden": components["gi_burden"],
                "gi_coefficient": gi_coefficient,
                "medication_missed": bool(medication_missed),
                "medicated": bool(profile.medicated),
                "routine_load": components["routine_load"],
                "sensory_load": components["sensory_load"],
                "p_crisis_next_day": next_probability,
                "crisis_next_day": next_crisis,
                "current_crisis": current_crisis,
                "support_level": profile.support_level,
                "verbal": profile.verbal,
                "chronic_gi": bool(profile.chronic_gi),
                "sex": profile.sex,
                "sleep_need": profile.sleep_need,
                "susceptibility": profile.susceptibility,
                "noise_std": profile.noise_std,
                "base_rate_i": profile.base_rate_i,
                "dysregulation_signal_unmasked": raw_dysregulation_signal,
                "dysregulation_signal_observed": observed_dysregulation_signal,
                "behavior_tag_count_true": len(true_tags),
                "behavior_tag_count_observed": len(observed_tags),
            }
        )
        sleep_deficits.append(float(components["sleep_deficit"]))
        gi_burdens.append(float(components["gi_burden_current"]))
        routine_events.append(float(routine_changes))
        previous_load = latent_load
        current_crisis = next_crisis

    return logs, ground_truth


def _set_log_dtypes(logs: pd.DataFrame) -> pd.DataFrame:
    integer_fields = (*ORDINAL_FIELDS, "night_awakenings", "dysregulation_events")
    for field_name in integer_fields:
        logs[field_name] = logs[field_name].astype("Int64")
    logs["sleep_hours"] = logs["sleep_hours"].astype("Float64")
    for field_name in BOOLEAN_FIELDS:
        logs[field_name] = logs[field_name].astype("boolean")
    return logs


def _manifest(
    *,
    n_children: int,
    days: int,
    seed: int,
    start_date: date,
    coefficients: Mapping[str, float] = SYNTH_COEFFICIENTS,
) -> dict[str, Any]:
    return {
        "generator_version": SYNTH_GENERATOR_VERSION,
        "spec_version": SPEC_VERSION,
        "seed": seed,
        "population": {
            "n_children": n_children,
            "days": days,
            "start_date": start_date.isoformat(),
        },
        "causal_model": {
            "coefficients": dict(coefficients),
            "noise_std": SYNTH_NOISE_STD,
            "susceptibility_std": SYNTH_SUSCEPTIBILITY_STD,
            "sleep_debt_weights": list(SYNTH_SLEEP_DEBT_WEIGHTS),
            "gi_burden_weights": list(SYNTH_GI_BURDEN_WEIGHTS),
            "routine_load_weights": list(SYNTH_ROUTINE_LOAD_WEIGHTS),
            "causal_iterations": SYNTH_CAUSAL_ITERATIONS,
        },
        "profiles": {
            "support_low_probability": SYNTH_SUPPORT_LOW_PROBABILITY,
            "high_support_noise_multiplier": SYNTH_HIGH_SUPPORT_NOISE_MULTIPLIER,
            "verbal_probability": SYNTH_VERBAL_PROBABILITY,
            "chronic_gi_probability": SYNTH_CHRONIC_GI_PROBABILITY,
            "female_probability": SYNTH_FEMALE_PROBABILITY,
            "female_signal_factor": SYNTH_FEMALE_SIGNAL_FACTOR,
            "nonverbal_gi_multiplier": SYNTH_NONVERBAL_GI_MULTIPLIER,
            "sleep_need": {
                "mean": SYNTH_SLEEP_NEED_MEAN,
                "std": SYNTH_SLEEP_NEED_STD,
                "min": SYNTH_SLEEP_NEED_MIN,
                "max": SYNTH_SLEEP_NEED_MAX,
            },
            "personal_base_rate": {
                "min": SYNTH_PERSONAL_BASE_RATE_MIN,
                "max": SYNTH_PERSONAL_BASE_RATE_MAX,
            },
        },
        "observation_model": {
            "sleep_load_factor": SYNTH_SLEEP_LOAD_FACTOR,
            "sleep_load_divisor": SYNTH_SLEEP_LOAD_DIVISOR,
            "sleep_noise_std": SYNTH_SLEEP_NOISE_STD,
            "sleep_min": SYNTH_SLEEP_OBSERVED_MIN,
            "sleep_max": SYNTH_SLEEP_OBSERVED_MAX,
            "awakenings_base": SYNTH_AWAKENINGS_BASE,
            "awakenings_load_factor": SYNTH_AWAKENINGS_LOAD_FACTOR,
            "gi_chronic_penalty": SYNTH_GI_CHRONIC_PENALTY,
            "gi_noise_std": SYNTH_GI_NOISE_STD,
            "alertness_noise_std": SYNTH_ALERTNESS_NOISE_STD,
            "state_noise_std": SYNTH_STATE_NOISE_STD,
            "participation_noise_std": SYNTH_PARTICIPATION_NOISE_STD,
            "dysregulation_load_factor": SYNTH_DYSREGULATION_LOAD_FACTOR,
            "dysregulation_noise_mean": SYNTH_DYSREGULATION_NOISE_MEAN,
            "dysregulation_noise_std": SYNTH_DYSREGULATION_NOISE_STD,
            "event_probability_min": SYNTH_EVENT_PROBABILITY_MIN,
            "event_probability_max": SYNTH_EVENT_PROBABILITY_MAX,
        },
        "missingness": {
            "base": SYNTH_MISSING_BASE,
            "load_factor": SYNTH_MISSING_LOAD_FACTOR,
            "load_offset": SYNTH_MISSING_LOAD_OFFSET,
            "maximum": SYNTH_MISSING_MAX,
            "forgetful_multiplier": SYNTH_MISSING_FORGETFUL_MULTIPLIER,
            "sleep_multiplier": SYNTH_MISSING_SLEEP_MULTIPLIER,
        },
        "sources": {
            "school_weekend_start": SYNTH_WEEKEND_START,
            "therapy_weekdays": list(SYNTH_THERAPY_WEEKDAYS),
            "days_per_week": SYNTH_DAYS_PER_WEEK,
        },
    }


def generate_synthetic_data(
    *,
    n_children: int = SYNTH_N_CHILDREN,
    days: int = SYNTH_DAYS,
    seed: int = RANDOM_SEED,
    start_date: date | None = None,
    coefficients: Mapping[str, float] | None = None,
) -> SyntheticDataset:
    """Generate deterministic logs and unobserved causal ground truth in memory.

    ``coefficients`` overrides the fixed causal weights of SPEC 8.2. It exists
    for the misspecification test of SPEC 13.2, which must evaluate a model
    trained on these parameters against data generated with different ones.
    """
    effective_coefficients = {**SYNTH_COEFFICIENTS, **(coefficients or {})}
    effective_start_date = start_date or date.fromisoformat(SYNTH_START_DATE)
    profile_rng = np.random.default_rng(np.random.SeedSequence([seed, 0]))
    profiles = _profile_table(profile_rng, n_children, seed, effective_coefficients)
    logs: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []
    for _, profile in profiles.iterrows():
        child_rng = np.random.default_rng(
            np.random.SeedSequence([seed, int(profile.child_index), 1])
        )
        child_logs, child_truth = _generate_child(
            rng=child_rng,
            seed=seed,
            profile=profile,
            start_date=effective_start_date,
            days=days,
            coefficients=effective_coefficients,
        )
        logs.extend(child_logs)
        ground_truth.extend(child_truth)

    logs_frame = _set_log_dtypes(
        pd.DataFrame(logs).sort_values(["child_id", "date", "source"], ignore_index=True)
    )
    truth_frame = pd.DataFrame(ground_truth).sort_values(["child_id", "date"], ignore_index=True)
    return SyntheticDataset(
        logs=logs_frame,
        ground_truth=truth_frame,
        manifest=_manifest(
            n_children=n_children,
            days=days,
            seed=seed,
            start_date=effective_start_date,
            coefficients=effective_coefficients,
        ),
    )


def write_dataset(dataset: SyntheticDataset, output_dir: Path) -> None:
    """Write stable Parquet and JSON artifacts without embedding local paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset.logs.to_parquet(output_dir / "logs.parquet", index=False, compression="zstd")
    dataset.ground_truth.to_parquet(
        output_dir / "ground_truth.parquet", index=False, compression="zstd"
    )
    manifest_json = json.dumps(
        dataset.manifest,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    (output_dir / "manifest.json").write_text(f"{manifest_json}\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Faro synthetic data")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--children", type=int, default=SYNTH_N_CHILDREN)
    parser.add_argument("--days", type=int, default=SYNTH_DAYS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--start-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    dataset = generate_synthetic_data(
        n_children=args.children,
        days=args.days,
        seed=args.seed,
        start_date=args.start_date,
    )
    write_dataset(dataset, args.output_dir)


if __name__ == "__main__":
    main()
