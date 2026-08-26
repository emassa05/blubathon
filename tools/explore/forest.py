"""Bosque aleatorio con importancia por permutación, repetido sobre semillas.

La importancia por defecto de scikit-learn (reducción de impureza) está sesgada
hacia variables con más categorías: una variable con seis valores tiene más
formas de cortar que una con dos y aparece más importante aunque no informe
nada. Con `sleep_quality` en tres categorías y `medication_adherence` en dos,
ese sesgo bastaría para producir el ranking que uno espera ver.

La importancia por permutación no tiene ese sesgo y además se explica en una
frase: se baraja una columna, se vuelve a medir, y lo que empeora es lo que esa
columna aportaba.

La importancia se mide **fuera de muestra**, dejando un sujeto afuera, igual que
el Brier del challenger. Medirla sobre los mismos datos con los que se ajustó el
bosque responde otra pregunta —cuánto memorizó el bosque esa columna— y con 7
eventos un bosque memoriza todo: hecho así, cinco de seis variables salen con
importancia negativa, que es la firma del sobreajuste, no un hallazgo.

Lo que reporta este módulo no es el ranking sino su **estabilidad**. Un bosque
siempre devuelve un orden; la pregunta útil es si ese orden sobrevive al cambio
de semilla. Si no sobrevive, el ranking era ruido con formato de tabla.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import OrdinalEncoder

from tools.explore.features import FeatureMatrix

DEFAULT_SEEDS = 20
DEFAULT_TREES = 500
PERMUTATION_REPEATS = 10


@dataclass(frozen=True, slots=True)
class VariableStability:
    """Cómo se comportó una variable a lo largo de las semillas."""

    name: str
    mean_rank: float
    best_rank: int
    worst_rank: int
    times_first: int
    mean_importance: float
    sd_importance: float

    @property
    def rank_span(self) -> str:
        return f"{self.best_rank}-{self.worst_rank}"


@dataclass(frozen=True, slots=True)
class StabilityReport:
    variables: tuple[VariableStability, ...]
    seeds: int
    n_rows: int
    n_positive: int
    majority_class_accuracy: float

    @property
    def is_stable(self) -> bool:
        """Estable = una sola variable se lleva el primer puesto siempre."""

        return bool(self.variables) and any(
            variable.times_first == self.seeds for variable in self.variables
        )

    @property
    def none_helps(self) -> bool:
        """Toda importancia negativa: el bosque predice mejor sin ninguna variable."""

        return bool(self.variables) and all(
            variable.mean_importance <= 0.0 for variable in self.variables
        )


def _encode(matrix: FeatureMatrix) -> tuple[np.ndarray, np.ndarray]:
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    features = encoder.fit_transform(np.array(matrix.rows, dtype=object))
    return features, np.array(matrix.labels, dtype=int)


def importance_stability(
    matrix: FeatureMatrix,
    *,
    seeds: int = DEFAULT_SEEDS,
    trees: int = DEFAULT_TREES,
) -> StabilityReport:
    """Ajusta un bosque por semilla y acumula el puesto de cada variable.

    `class_weight='balanced'` porque con 7% de prevalencia un bosque sin pesos
    aprende a decir siempre que no y acierta el 93%.
    """

    features, labels = _encode(matrix)
    groups = np.array(matrix.subjects)
    ranks: dict[str, list[int]] = {name: [] for name in matrix.columns}
    importances: dict[str, list[float]] = {name: [] for name in matrix.columns}

    for seed in range(seeds):
        totals = dict.fromkeys(matrix.columns, 0.0)
        folds = 0
        for held_out in np.unique(groups):
            train = groups != held_out
            test = groups == held_out
            # Un pliegue sin ambas clases no define una mejora al permutar.
            if len(np.unique(labels[train])) < 2 or len(np.unique(labels[test])) < 2:
                continue
            forest = RandomForestClassifier(
                n_estimators=trees,
                class_weight="balanced",
                random_state=seed,
                n_jobs=1,
            )
            forest.fit(features[train], labels[train])
            result = permutation_importance(
                forest,
                features[test],
                labels[test],
                n_repeats=PERMUTATION_REPEATS,
                random_state=seed,
                scoring="neg_brier_score",
            )
            for name, score in zip(matrix.columns, result.importances_mean, strict=True):
                totals[name] += float(score)
            folds += 1

        if not folds:
            continue
        scores = {name: total / folds for name, total in totals.items()}
        ordered = sorted(matrix.columns, key=lambda name: scores[name], reverse=True)
        for position, name in enumerate(ordered, start=1):
            ranks[name].append(position)
        for name, score in scores.items():
            importances[name].append(score)

    if not any(ranks.values()):
        return StabilityReport(
            variables=(),
            seeds=seeds,
            n_rows=len(matrix.labels),
            n_positive=matrix.positives,
            majority_class_accuracy=1.0 - matrix.prevalence,
        )

    variables = tuple(
        sorted(
            (
                VariableStability(
                    name=name,
                    mean_rank=mean(ranks[name]),
                    best_rank=min(ranks[name]),
                    worst_rank=max(ranks[name]),
                    times_first=sum(1 for rank in ranks[name] if rank == 1),
                    mean_importance=mean(importances[name]),
                    sd_importance=pstdev(importances[name]),
                )
                for name in matrix.columns
            ),
            key=lambda variable: variable.mean_rank,
        )
    )

    majority = 1.0 - matrix.prevalence
    return StabilityReport(
        variables=variables,
        seeds=seeds,
        n_rows=len(matrix.labels),
        n_positive=matrix.positives,
        majority_class_accuracy=majority,
    )
