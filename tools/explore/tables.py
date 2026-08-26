"""Tabla de frecuencias: de los días con cada valor, cuántos terminaron en crisis.

Es contar. Se agrupan los días por el valor que tuvo una variable, se cuenta
cuántos de esos días fueron seguidos de una crisis y se divide. No hay modelo
ajustándose a nada, así que no hay nada que se pueda sobreajustar ni ningún
resultado que dependa de una semilla.

Lo que sí hay que cuidar es cuándo una celda es legible. Con una prevalencia del
7%, un valor observado 8 días espera 0,55 crisis: va a mostrar 0% o 12,5% según
caiga una sola, y ninguna de las dos cifras mide nada. Por eso las celdas por
debajo de `MIN_DAYS` se muestran pero no entran en la comparación entre valores.

La tabla junta a los cuatro niños. Cada uno tiene su propia tasa base —es
exactamente lo que estima el baseline personal— así que un valor que aparezca
sobre todo en el niño de tasa alta va a mostrar una tasa alta por eso y no por
la variable. Con 7 eventos no alcanza para separar las dos cosas, y la salida lo
dice en vez de esconderlo.
"""

from __future__ import annotations

from dataclasses import dataclass

from tools.explore.features import FeatureMatrix

# Días mínimos para que la tasa de una celda sea comparable con otra. Bajo la
# prevalencia observada, menos que esto no alcanza para esperar una sola crisis.
MIN_DAYS = 15


@dataclass(frozen=True, slots=True)
class ValueCount:
    """Un valor de una variable y el desenlace de los días en que se observó."""

    value: str
    days: int
    crises: int
    subjects: int

    @property
    def rate(self) -> float:
        return self.crises / self.days if self.days else 0.0

    @property
    def is_comparable(self) -> bool:
        return self.days >= MIN_DAYS


@dataclass(frozen=True, slots=True)
class VariableTable:
    """Todos los valores de una variable, del más frecuente al menos frecuente."""

    name: str
    values: tuple[ValueCount, ...]

    @property
    def comparable(self) -> tuple[ValueCount, ...]:
        return tuple(value for value in self.values if value.is_comparable)

    @property
    def spread(self) -> float | None:
        """Distancia entre la tasa más alta y la más baja entre celdas legibles.

        Es la señal cruda de la variable: cuánto se mueve el riesgo entre una
        respuesta y otra. `None` cuando queda menos de un par que comparar.
        """

        rates = [value.rate for value in self.comparable]
        return max(rates) - min(rates) if len(rates) > 1 else None


@dataclass(frozen=True, slots=True)
class FrequencyReport:
    variables: tuple[VariableTable, ...]
    n_rows: int
    n_positive: int
    prevalence: float

    @property
    def any_comparable(self) -> bool:
        return any(variable.spread is not None for variable in self.variables)


def build_tables(matrix: FeatureMatrix) -> FrequencyReport:
    """Cuenta días y crisis por valor, ordenando las variables por su spread."""

    tables: list[VariableTable] = []
    for position, name in enumerate(matrix.columns):
        days: dict[str, int] = {}
        crises: dict[str, int] = {}
        subjects: dict[str, set[str]] = {}
        for row, label, subject_id in zip(matrix.rows, matrix.labels, matrix.subjects, strict=True):
            value = row[position]
            if value is None:
                continue
            days[value] = days.get(value, 0) + 1
            crises[value] = crises.get(value, 0) + label
            subjects.setdefault(value, set()).add(subject_id)

        values = tuple(
            sorted(
                (
                    ValueCount(
                        value=value,
                        days=count,
                        crises=crises[value],
                        subjects=len(subjects[value]),
                    )
                    for value, count in days.items()
                ),
                key=lambda entry: entry.days,
                reverse=True,
            )
        )
        tables.append(VariableTable(name=name, values=values))

    # Las variables sin celdas comparables van al final: no es que su señal sea
    # cero, es que no hay días suficientes para verla.
    ordered = tuple(
        sorted(
            tables,
            key=lambda table: (table.spread is not None, table.spread or 0.0),
            reverse=True,
        )
    )
    return FrequencyReport(
        variables=ordered,
        n_rows=len(matrix.labels),
        n_positive=matrix.positives,
        prevalence=matrix.prevalence,
    )
