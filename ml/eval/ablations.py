"""Ablaciones — SPEC §13.1, §13.2.

Nota de alcance: la evaluación completa de estas ablaciones (200 niños x
180 días) requiere el generador sintético `ml/synth` (§8), zona de P1
(~5h) aún no construida. Lo que sigue son las funciones **puras** del
modelo de adherencia y de la composición de máscaras — la parte que le
corresponde a P2 y que se puede probar con arreglos sintéticos pequeños
sin depender del generador. `run_elicitation_ablation` queda lista para
recibir logs reales de `ml/synth` en cuanto existan.
"""

from __future__ import annotations

from ml.spec_constants import (
    ELICITATION_POLICY_QUESTIONS,
    ELICITATION_RESPONSE_INTERCEPT,
    ELICITATION_RESPONSE_MAX,
    ELICITATION_RESPONSE_MIN,
    ELICITATION_RESPONSE_SLOPE,
    STALE_CHANGE_THRESHOLD_POINTS,
)


def adherence_probability(n_questions: int) -> float:
    """SPEC §13.1 — `p_responde(n) = clip(0.95 - 0.045·n, 0.30, 0.95)`."""
    raw = ELICITATION_RESPONSE_INTERCEPT - ELICITATION_RESPONSE_SLOPE * n_questions
    return max(ELICITATION_RESPONSE_MIN, min(ELICITATION_RESPONSE_MAX, raw))


POLICY_QUESTIONS_PER_DAY = ELICITATION_POLICY_QUESTIONS


def apply_policy_mask(responded_by_field: dict[str, bool], policy: str) -> dict[str, bool]:
    """(a) política pregunta ∧ (b) persona responde (NMAR ya aplicado en
    `responded_by_field`, que ya refleja si la persona iba a responder)."""
    n_questions = POLICY_QUESTIONS_PER_DAY[policy]
    adherence = adherence_probability(n_questions)
    return {
        field: (responded and adherence >= 0.30) for field, responded in responded_by_field.items()
    }


def stale_variable_miss_rate(days: list[dict]) -> float:
    """% de días en que una variable de HIGH_WEIGHT cambió >= 2 puntos
    respecto de su última observación y la política no la preguntó ese día.

    `days`: lista de {"delta": float, "asked": bool} por variable-día ya
    filtrada a HIGH_WEIGHT.
    """
    if not days:
        return 0.0
    misses = sum(
        1 for d in days if abs(d["delta"]) >= STALE_CHANGE_THRESHOLD_POINTS and not d["asked"]
    )
    return misses / len(days)


def run_elicitation_ablation(
    y_true: list[int],
    y_score_by_policy: dict[str, list[float]],
    status_by_policy: dict[str, list[str]],
) -> dict:
    """SPEC §13.1 — tabla de políticas A/B/C/D. `y_score_by_policy` y
    `status_by_policy` ya vienen recalculados bajo cada política (fuera de
    este módulo, sobre logs con la máscara de §13.1 aplicada)."""
    from ml.eval.metrics import average_precision, decision_coverage

    table = {}
    for policy, scores in y_score_by_policy.items():
        table[policy] = {
            "questions_per_day": POLICY_QUESTIONS_PER_DAY[policy],
            "adherence": adherence_probability(POLICY_QUESTIONS_PER_DAY[policy]),
            "auc_pr": average_precision(y_true, scores),
            "decision_coverage": decision_coverage(status_by_policy[policy]),
        }
    return table


def run_misspecification_test(
    auc_pr_train_params: float, auc_pr_perturbed: dict[str, float]
) -> dict:
    """SPEC §13.2 — caída de `auc_pr` al evaluar con parámetros perturbados
    (semillas 142-144, betas x U(0.7,1.3), rho in {0.15,0.45}, base_rate in
    {0.06,0.16}). `auc_pr_perturbed` ya viene calculado por el caller sobre
    cada dataset perturbado."""
    return {
        "auc_pr_reference": auc_pr_train_params,
        "auc_pr_perturbed": auc_pr_perturbed,
        "drop": {
            seed: round(auc_pr_train_params - value, 4) for seed, value in auc_pr_perturbed.items()
        },
    }
