"""Métricas de evaluación — SPEC §13. Funciones puras: `y_true, y_pred -> dict`."""

from __future__ import annotations


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def average_precision(y_true: list[int], y_score: list[float]) -> float:
    """`auc_pr` — average precision (área bajo la curva precisión-recall)."""
    n_pos = sum(y_true)
    if n_pos == 0:
        return 0.0
    order = sorted(range(len(y_score)), key=lambda i: -y_score[i])
    tp = fp = 0
    prev_recall = 0.0
    ap = 0.0
    for i in order:
        if y_true[i] == 1:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp)
        recall = tp / n_pos
        ap += precision * (recall - prev_recall)
        prev_recall = recall
    return ap


def auc_roc(y_true: list[int], y_score: list[float]) -> float:
    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    pos_scores = [s for s, y in zip(y_score, y_true, strict=True) if y == 1]
    neg_scores = [s for s, y in zip(y_score, y_true, strict=True) if y == 0]
    wins = 0.0
    for ps in pos_scores:
        for ns in neg_scores:
            if ps > ns:
                wins += 1
            elif ps == ns:
                wins += 0.5
    return wins / (n_pos * n_neg)


def brier_score(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true:
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(y_prob, y_true, strict=True)) / len(y_true)


def expected_calibration_error(y_true: list[int], y_prob: list[float], n_bins: int = 10) -> float:
    """`ece` con `n_bins` bins de igual ancho en [0,1]."""
    if not y_true:
        return 0.0
    bins = [[] for _ in range(n_bins)]
    for p, y in zip(y_prob, y_true, strict=True):
        idx = min(n_bins - 1, int(_clip01(p) * n_bins))
        bins[idx].append((p, y))
    n = len(y_true)
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        conf = sum(p for p, _ in bucket) / len(bucket)
        acc = sum(y for _, y in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(conf - acc)
    return ece


def alert_budget_recall(
    y_true: list[int], y_score: list[float], child_ids: list[str], budget_per_child: int
) -> dict:
    """Recall de crisis con presupuesto de `budget_per_child` alertas por niño
    (SPEC §13: se reporta como curva; aquí, el punto para el presupuesto dado
    más la curva completa 1..N)."""
    by_child: dict[str, list[tuple[float, int]]] = {}
    for cid, s, y in zip(child_ids, y_score, y_true, strict=True):
        by_child.setdefault(cid, []).append((s, y))

    def recall_at(budget: int) -> float:
        tp = 0
        total_pos = sum(y_true)
        if total_pos == 0:
            return 0.0
        for pairs in by_child.values():
            top = sorted(pairs, key=lambda p: -p[0])[:budget]
            tp += sum(y for _, y in top)
        return tp / total_pos

    max_budget = max((len(v) for v in by_child.values()), default=1)
    curve = {b: recall_at(b) for b in range(1, max_budget + 1)}
    return {"at_budget": recall_at(budget_per_child), "curve": curve}


def decision_coverage(statuses: list[str]) -> float:
    """% de días-niño con `status == 'ok'` (no abstiene)."""
    if not statuses:
        return 0.0
    return sum(1 for s in statuses if s == "ok") / len(statuses)


def fairness_sex(y_true: list[int], y_score: list[float], sex: list[str]) -> dict:
    """`auc_pr` y recall por sexo (F vs M), reportado honestamente."""
    out = {}
    for group in ("F", "M"):
        idx = [i for i, s in enumerate(sex) if s == group]
        if not idx:
            out[group] = {"auc_pr": None, "recall_at_10pct": None, "n": 0}
            continue
        yt = [y_true[i] for i in idx]
        ys = [y_score[i] for i in idx]
        n_pos = sum(yt)
        if n_pos == 0:
            recall = None
        else:
            k = max(1, round(0.10 * len(yt)))
            top = sorted(range(len(ys)), key=lambda i: -ys[i])[:k]
            recall = sum(yt[i] for i in top) / n_pos
        out[group] = {"auc_pr": average_precision(yt, ys), "recall_at_10pct": recall, "n": len(idx)}
    return out


def baseline_always_base_rate(y_true: list[int]) -> list[float]:
    """Baseline obligatorio 1 (§13): predecir siempre la tasa base."""
    rate = sum(y_true) / len(y_true) if y_true else 0.0
    return [rate] * len(y_true)


def baseline_yesterday_dysregulation(dysregulation_yesterday: list[bool]) -> list[float]:
    """Baseline obligatorio 2 (§13): 'ayer hubo desregulación -> mañana crisis'."""
    return [1.0 if d else 0.0 for d in dysregulation_yesterday]


def evaluate(y_true: list[int], y_score: list[float]) -> dict:
    """Métricas puntuales sobre un test set: `y_true, y_pred -> dict`."""
    return {
        "auc_pr": average_precision(y_true, y_score),
        "auc_roc": auc_roc(y_true, y_score),
        "brier": brier_score(y_true, y_score),
        "ece": expected_calibration_error(y_true, y_score),
        "lead_time_hours": 24,
    }
