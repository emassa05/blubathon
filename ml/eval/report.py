"""The full evaluation of SPEC 13, computed once at training time.

Every number here is measured on held-out children. The report is built offline
and stored with the model so ``/eval`` serves it instantly instead of re-scoring
thirty-six thousand rows per request.

What these numbers are: evidence that the pipeline works and survives different
assumptions. What they are not: a claim about real children. That needs
validation on Bluba data, and the protocol is the proposed next step.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from ml.engine.model import RiskEnsemble, SupervisedDataset, build_supervised_dataset
from ml.eval.ablations import (
    POLICY_QUESTIONS_PER_DAY,
    adherence_probability,
    stale_variable_miss_rate,
)
from ml.eval.metrics import (
    alert_budget_recall,
    average_precision,
    baseline_always_base_rate,
    baseline_yesterday_dysregulation,
    expected_calibration_error,
)
from ml.features import compute_icd
from ml.spec_constants import (
    ABSTAIN_ICD,
    ABSTAIN_WIDTH,
    ELICITATION_POLICY_QUESTIONS,
    EVALUATION_ALERT_BUDGET_PER_CHILD,
    HIGH_WEIGHT_FIELDS,
    ICD_WEIGHTS,
    MISSPECIFICATION_BASE_RATES,
    MISSPECIFICATION_BETA_MAX,
    MISSPECIFICATION_BETA_MIN,
    MISSPECIFICATION_CARRYOVERS,
    MISSPECIFICATION_SEEDS,
    MODEL_INPUT_FIELDS,
    PREDICTION_HORIZON_DAYS,
    RANDOM_SEED,
    RISK_API_DECIMALS,
    SYNTH_COEFFICIENTS,
)

# Forcing p_miss to one half is the robustness ablation named in SPEC 13.
FORCED_MISSING_RATE = 0.50
# ICD is expensive per row, so decision coverage is measured on a deterministic
# sample of held-out child-days rather than all of them.
_COVERAGE_DAYS_PER_CHILD = 20


def _round(value: float) -> float:
    return round(float(value), RISK_API_DECIMALS)


def _test_slice(
    ensemble: RiskEnsemble, supervised: SupervisedDataset
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    mask = np.isin(supervised.child_ids, list(ensemble.split_.test))
    return (
        supervised.features.loc[mask].reset_index(drop=True),
        supervised.target[mask],
        supervised.child_ids[mask],
    )


def _yesterday_dysregulation(features: pd.DataFrame) -> list[bool]:
    column = features["dysregulation_events"]
    return [bool(value) if pd.notna(value) else False for value in column]


def core_metrics(
    ensemble: RiskEnsemble, supervised: SupervisedDataset
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    """The point metrics of SPEC 13 over every held-out child-day."""
    features, target, child_ids = _test_slice(ensemble, supervised)
    probability = ensemble.predict(features).probability
    base = ensemble.evaluate(supervised.features, supervised.target, supervised.child_ids)
    recall = alert_budget_recall(
        list(target), list(probability), list(child_ids), EVALUATION_ALERT_BUDGET_PER_CHILD
    )
    metrics = {
        "auc_pr": _round(base["auc_pr"]),
        "auc_roc": _round(base["auc_roc"]),
        "brier": _round(base["brier"]),
        "ece": _round(expected_calibration_error(list(target), list(probability))),
        "base_rate": _round(base["base_rate"]),
        "lead_time_hours": 24 * PREDICTION_HORIZON_DAYS,
        "n_evaluated": len(target),
        "alert_budget_recall": {
            "budget_per_child_week": EVALUATION_ALERT_BUDGET_PER_CHILD,
            "at_budget": _round(recall["at_budget"]),
            "curve": {
                str(budget): _round(value) for budget, value in sorted(recall["curve"].items())[:7]
            },
        },
    }
    return metrics, features, target, probability


def mandatory_baselines(
    ensemble: RiskEnsemble, supervised: SupervisedDataset
) -> dict[str, dict[str, float]]:
    """The two comparisons SPEC 13 requires Faro to beat."""
    features, target, _ = _test_slice(ensemble, supervised)
    labels = list(target)
    return {
        "always_base_rate": {
            "auc_pr": _round(average_precision(labels, baseline_always_base_rate(labels)))
        },
        "yesterday_dysregulation": {
            "auc_pr": _round(
                average_precision(
                    labels,
                    baseline_yesterday_dysregulation(_yesterday_dysregulation(features)),
                )
            )
        },
    }


def decision_coverage_report(
    ensemble: RiskEnsemble,
    logs: pd.DataFrame,
    supervised: SupervisedDataset,
) -> dict[str, float]:
    """Share of held-out child-days where the system commits to a number.

    ICD costs a scan of the fourteen-day window per row, so this samples a fixed
    number of days per held-out child with the project seed rather than scoring
    every row (SPEC rule 0.9 keeps the sample reproducible).
    """
    rng = np.random.default_rng(RANDOM_SEED)
    mask = np.isin(supervised.child_ids, list(ensemble.split_.test))
    features = supervised.features.loc[mask].reset_index(drop=True)
    child_ids = supervised.child_ids[mask]
    dates = supervised.dates[mask]
    widths = ensemble.predict(features).width

    history_by_child: dict[str, list[dict[str, Any]]] = {}
    for record in logs.to_dict("records"):
        history_by_child.setdefault(str(record["child_id"]), []).append(record)

    committed = 0
    total = 0
    for child_id in sorted(set(child_ids)):
        positions = np.flatnonzero(child_ids == child_id)
        sampled = rng.choice(
            positions, size=min(_COVERAGE_DAYS_PER_CHILD, len(positions)), replace=False
        )
        history = history_by_child.get(str(child_id), [])
        for position in sampled:
            day = dates[position]
            visible = [record for record in history if str(record["date"]) <= str(day.date())]
            quality = compute_icd(visible, day)
            total += 1
            if quality["icd"] >= ABSTAIN_ICD and widths[position] <= ABSTAIN_WIDTH:
                committed += 1
    return {"decision_coverage": _round(committed / total) if total else 0.0}


def fairness_by_sex(
    ensemble: RiskEnsemble,
    supervised: SupervisedDataset,
    ground_truth: pd.DataFrame,
) -> dict[str, Any]:
    """AUC-PR and top-decile recall per sex, reported whatever it says.

    Girls are under-recorded in the generator by design (SPEC 8.4), so this is
    the number most likely to be uncomfortable, and the reason it is here.
    """
    features, target, child_ids = _test_slice(ensemble, supervised)
    probability = ensemble.predict(features).probability
    sex_by_child = (
        ground_truth.drop_duplicates("child_id").set_index("child_id")["sex"].astype(str).to_dict()
    )
    report: dict[str, Any] = {}
    for group in ("F", "M"):
        positions = [
            index
            for index, child_id in enumerate(child_ids)
            if sex_by_child.get(str(child_id)) == group
        ]
        if not positions:
            report[group] = {"auc_pr": None, "recall_at_10pct": None, "n": 0}
            continue
        labels = [int(target[index]) for index in positions]
        scores = [float(probability[index]) for index in positions]
        positives = sum(labels)
        recall = None
        if positives:
            top = sorted(range(len(scores)), key=lambda i: -scores[i])[
                : max(1, round(0.10 * len(scores)))
            ]
            recall = _round(sum(labels[i] for i in top) / positives)
        report[group] = {
            "auc_pr": _round(average_precision(labels, scores)),
            "recall_at_10pct": recall,
            "n": len(positions),
        }
    both = [report[group]["auc_pr"] for group in ("F", "M") if report[group]["auc_pr"] is not None]
    report["auc_pr_gap"] = _round(abs(both[0] - both[1])) if len(both) == 2 else None
    return report


def _retrain_without(
    supervised: SupervisedDataset, dropped: Sequence[str]
) -> tuple[RiskEnsemble, float]:
    keep = [column for column in supervised.features.columns if column not in set(dropped)]
    ensemble = RiskEnsemble().fit(
        supervised.features[keep], supervised.target, supervised.child_ids
    )
    scores = ensemble.evaluate(supervised.features[keep], supervised.target, supervised.child_ids)
    return ensemble, float(scores["auc_pr"])


def _sleep_columns(features: pd.DataFrame) -> list[str]:
    return [column for column in features.columns if column.startswith(("sleep_", "night_awak"))]


def _personal_baseline_columns(features: pd.DataFrame) -> list[str]:
    return [column for column in features.columns if column.endswith("_z")]


def mask_observations(features: pd.DataFrame, rate: float, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Hide a share of observed answers, keeping the missing flags truthful."""
    rng = np.random.default_rng(seed)
    masked = features.copy()
    for variable in MODEL_INPUT_FIELDS:
        if variable not in masked:
            continue
        derived = [
            column
            for column in masked.columns
            if column == variable or column.startswith(f"{variable}_")
        ]
        hide = rng.random(len(masked)) < rate
        for column in derived:
            if column.endswith("_missing"):
                masked.loc[hide, column] = 1.0
            else:
                masked.loc[hide, column] = np.nan
    return masked


def feature_ablations(ensemble: RiskEnsemble, supervised: SupervisedDataset) -> dict[str, Any]:
    """SPEC 13: what the model loses without sleep, without C1, and with worse data."""
    reference = float(
        ensemble.evaluate(supervised.features, supervised.target, supervised.child_ids)["auc_pr"]
    )
    _, without_sleep = _retrain_without(supervised, _sleep_columns(supervised.features))
    _, without_baseline = _retrain_without(
        supervised, _personal_baseline_columns(supervised.features)
    )
    features, target, _ = _test_slice(ensemble, supervised)
    degraded = ensemble.predict(mask_observations(features, FORCED_MISSING_RATE)).probability
    forced_missing = average_precision(list(target), list(degraded))
    return {
        "reference_auc_pr": _round(reference),
        "without_sleep": {
            "auc_pr": _round(without_sleep),
            "delta": _round(without_sleep - reference),
        },
        "without_personal_baseline": {
            "auc_pr": _round(without_baseline),
            "delta": _round(without_baseline - reference),
        },
        "forced_missing_50pct": {
            "auc_pr": _round(forced_missing),
            "delta": _round(forced_missing - reference),
        },
    }


def _policy_kept_fields(policy: str) -> list[str]:
    """Which variables each elicitation policy actually asks about (SPEC 13.1)."""
    by_importance = sorted(ICD_WEIGHTS, key=lambda name: (-ICD_WEIGHTS[name], name))
    asked = ELICITATION_POLICY_QUESTIONS[policy]
    if policy == "A":
        return list(by_importance)
    return by_importance[:asked]


def elicitation_ablation(ensemble: RiskEnsemble, supervised: SupervisedDataset) -> dict[str, Any]:
    """SPEC 13.1: four question policies under the same fatigue model.

    A field is observed only if the policy asked about it and the person
    answered. More questions means lower adherence, so asking everything is not
    the same as knowing everything.
    """
    features, target, _ = _test_slice(ensemble, supervised)
    labels = list(target)
    table: dict[str, Any] = {}
    for policy in sorted(ELICITATION_POLICY_QUESTIONS):
        asked = set(_policy_kept_fields(policy))
        adherence = adherence_probability(POLICY_QUESTIONS_PER_DAY[policy])
        unasked = [variable for variable in MODEL_INPUT_FIELDS if variable not in asked]
        masked = features.copy()
        for variable in unasked:
            derived = [
                column
                for column in masked.columns
                if column == variable or column.startswith(f"{variable}_")
            ]
            for column in derived:
                masked[column] = 1.0 if column.endswith("_missing") else np.nan
        # Fatigue then removes a share of the answers the policy did ask for.
        masked = mask_observations(masked, 1.0 - adherence, seed=RANDOM_SEED + len(policy))
        prediction = ensemble.predict(masked)
        probability = prediction.probability
        widths = prediction.width
        table[policy] = {
            "questions_per_day": POLICY_QUESTIONS_PER_DAY[policy],
            "adherence": _round(adherence),
            "auc_pr": _round(average_precision(labels, list(probability))),
            "decision_coverage": _round(float(np.mean(widths <= ABSTAIN_WIDTH))),
        }
    _, _, child_ids = _test_slice(ensemble, supervised)
    table["D"]["stale_variable_miss_rate"] = _round(
        _stale_miss_rate(features, child_ids, set(_policy_kept_fields("D")))
    )
    table["B"]["stale_variable_miss_rate"] = _round(
        _stale_miss_rate(features, child_ids, set(_policy_kept_fields("B")), safeguards=True)
    )
    return table


def _stale_miss_rate(
    features: pd.DataFrame,
    child_ids: np.ndarray,
    asked: set[str],
    *,
    safeguards: bool = False,
) -> float:
    """How often a high-weight variable moved without the policy asking about it.

    With safeguards on, the staleness ceiling guarantees the variable is asked
    at least weekly, so only changes inside that window can be missed.
    """
    days: list[dict[str, float | bool]] = []
    for variable in sorted(HIGH_WEIGHT_FIELDS):
        if variable not in features:
            continue
        column = features[variable].astype(float)
        for child_id in sorted(set(child_ids)):
            positions = np.flatnonzero(child_ids == child_id)
            values = column.iloc[positions].to_numpy()
            deltas = np.abs(np.diff(values, prepend=values[:1]))
            for index, delta in enumerate(deltas):
                if np.isnan(delta):
                    continue
                was_asked = variable in asked or (safeguards and index % 7 == 0)
                days.append({"delta": float(delta), "asked": was_asked})
    return stale_variable_miss_rate(days)


def misspecification_test(
    ensemble: RiskEnsemble,
    generate: Any,
    *,
    n_children: int,
    days: int,
) -> dict[str, Any]:
    """SPEC 13.2: score the trained model against differently-generated worlds.

    Evaluating on the generator's own parameters is circular: the model
    rediscovers the coefficients we chose. Perturbing them bounds how much of
    the performance is the pipeline and how much is the setup.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    perturbed: dict[str, float] = {}
    for index, seed in enumerate(MISSPECIFICATION_SEEDS):
        coefficients = {
            name: value * float(rng.uniform(MISSPECIFICATION_BETA_MIN, MISSPECIFICATION_BETA_MAX))
            for name, value in SYNTH_COEFFICIENTS.items()
            if name not in {"intercept", "carryover"}
        }
        coefficients["carryover"] = MISSPECIFICATION_CARRYOVERS[
            index % len(MISSPECIFICATION_CARRYOVERS)
        ]
        base_rate = MISSPECIFICATION_BASE_RATES[index % len(MISSPECIFICATION_BASE_RATES)]
        coefficients["intercept"] = float(np.log(base_rate / (1 - base_rate)))
        dataset = generate(n_children=n_children, days=days, seed=seed, coefficients=coefficients)
        supervised = build_supervised_dataset(dataset.logs)
        aligned = supervised.features.reindex(columns=ensemble.feature_names_)
        probability = ensemble.predict(aligned).probability
        perturbed[str(seed)] = _round(average_precision(list(supervised.target), list(probability)))
    return perturbed


def build_report(
    ensemble: RiskEnsemble,
    logs: pd.DataFrame,
    ground_truth: pd.DataFrame,
    supervised: SupervisedDataset,
    *,
    generate: Any | None = None,
    misspecification_children: int = 40,
    misspecification_days: int = 90,
) -> dict[str, Any]:
    """Assemble every number SPEC 13 asks for into the /eval payload."""
    metrics, _, _, _ = core_metrics(ensemble, supervised)
    metrics.update(decision_coverage_report(ensemble, logs, supervised))
    report: dict[str, Any] = {
        "metrics": metrics,
        "baselines": mandatory_baselines(ensemble, supervised),
        "ablations": {
            "features": feature_ablations(ensemble, supervised),
            "elicitation": elicitation_ablation(ensemble, supervised),
            "fairness_sex": fairness_by_sex(ensemble, supervised, ground_truth),
        },
    }
    if generate is not None:
        reference = report["ablations"]["features"]["reference_auc_pr"]
        perturbed = misspecification_test(
            ensemble,
            generate,
            n_children=misspecification_children,
            days=misspecification_days,
        )
        report["ablations"]["misspecification"] = {
            "auc_pr_reference": reference,
            "auc_pr_perturbed": perturbed,
            "drop": {seed: _round(reference - value) for seed, value in perturbed.items()},
        }
    report["disclaimer_es"] = (
        "Estas métricas validan que el pipeline funciona y resiste supuestos distintos. "
        "No son una afirmación sobre el rendimiento con niños reales: eso requiere "
        "validación con datos de Bluba."
    )
    return report


def report_from_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Split a stored report into the three sections the API contract expects."""
    return {
        "metrics": dict(payload.get("metrics", {})),
        "baselines": dict(payload.get("baselines", {})),
        "ablations": dict(payload.get("ablations", {})),
    }
