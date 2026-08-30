"""Si lo que la cifra anuncia acaba pasando: la calibracion de la cohorte.

Una probabilidad no se puede comprobar en un dia. "Manana hay 56% de riesgo" no
es ni verdad ni mentira cuando llega manana: solo paso o no paso. Lo que si se
puede comprobar es el conjunto. De todos los dias en que se dijo mas o menos
56%, ?en cuantos hubo episodio? Si el modelo esta bien calibrado, en el 56%.

**Por cohorte y no por persona**, porque es lo unico que se puede medir en un
plazo util. Afirmar una frecuencia con +-10 puntos pide unos 97 dias **en cada
tramo**, y una persona reparte sus 365 dias al ano entre todos los tramos: con
cinco tramos son dos anos antes de poder decir nada. La misma cuenta con veinte
personas se cumple en un mes.

Lo que se pierde al juntar hay que decirlo: esto ya no responde "el modelo
acierta contigo", responde "el modelo acierta". Es la pregunta de si el sistema
sirve, no la de si te sirve a ti.

Y lo que esta medida **no** es, aunque se le parezca: no es la confianza de la
prediccion de hoy. Es la de todo el tramo, y la de hoy solo hereda la de su
tramo. Dos dias del mismo tramo comparten esta cifra aunque uno se apoye en
mucho mas historial que el otro.

Aviso que sobrevive a cualquier refinamiento: **el desenlace no se reporta a
ciegas**. Quien responde ve el porcentaje antes de decir si hubo episodio, asi
que la cifra que se esta evaluando influyo en la respuesta con la que se evalua.
Mientras eso siga asi, esta calibracion sale mejor de lo que es.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

#: 1.96 es el 95% de la normal. Se nombra porque aparece en la formula de Wilson
#: y un numero suelto ahi no se puede leer.
Z_95 = 1.959963984540054


def wilson(positivos: int, total: int, *, z: float = Z_95) -> tuple[float, float]:
    """El intervalo de Wilson para una proporcion observada.

    Wilson y no la normal de toda la vida —`p +- z*sqrt(p(1-p)/n)`— porque esa se
    rompe justo donde mas la vamos a usar. Con pocos dias, o con una frecuencia
    cerca de 0 o de 1, la normal se sale del [0, 1] y llega a dar intervalos de
    ancho cero: cero de veinte daria "entre 0% y 0%", que afirma muchisimo mas de
    lo que veinte dias pueden sostener. Wilson no se sale del rango y mantiene el
    ancho honesto en los extremos, que es el caso interesante: el tramo alto.
    """

    if total <= 0:
        return (0.0, 1.0)

    proporcion = positivos / total
    denominador = 1.0 + z * z / total
    centro = (proporcion + z * z / (2.0 * total)) / denominador
    margen = (
        z
        / denominador
        * math.sqrt(proporcion * (1.0 - proporcion) / total + z * z / (4.0 * total * total))
    )
    return (max(0.0, centro - margen), min(1.0, centro + margen))


@dataclass(frozen=True, slots=True)
class TramoCalibrado:
    """Un tramo de riesgo, con lo que anuncio y lo que de verdad ocurrio."""

    banda: str
    dias: int
    episodios: int
    #: La media de lo que el modelo anuncio en esos dias.
    anunciado: float
    #: La frecuencia con la que ocurrio de verdad.
    observado: float
    #: El intervalo de Wilson al 95% sobre `observado`.
    intervalo: tuple[float, float]

    @property
    def concuerda(self) -> bool:
        """Si lo anunciado cae dentro del intervalo de lo observado.

        Es la lectura entera de la calibracion en un booleano: el modelo dijo un
        numero, y los dias no lo desmienten. Que concuerde no lo confirma —un
        intervalo ancho no desmiente casi nada—, para eso esta `dias`.
        """

        return self.intervalo[0] <= self.anunciado <= self.intervalo[1]


@dataclass(frozen=True, slots=True)
class Calibracion:
    """La cohorte entera, tramo a tramo."""

    tramos: tuple[TramoCalibrado, ...]
    #: Brier sobre todos los dias, sin trocear. Mide lo mismo con cada dia una
    #: sola vez, asi que dice algo mucho antes de que los tramos se llenen.
    brier: float | None
    dias: int
    episodios: int

    @property
    def hay_datos(self) -> bool:
        return self.dias > 0


def calibrar(
    pares: Iterable[tuple[float, bool]],
    *,
    banda_de: Callable[[float], str],
    orden: Sequence[str],
) -> Calibracion:
    """Agrupa (probabilidad anunciada, ocurrio) por tramo y mide cada uno.

    `banda_de` llega de fuera y no se define aqui: los umbrales de las bandas son
    de la aplicacion, y tenerlos escritos en dos sitios seria tener dos
    definiciones de "riesgo alto" que se pueden separar sin que nadie lo note.
    Este modulo solo sabe agrupar y contar.

    `orden` fija en que orden salen los tramos, incluidos los que quedaron
    vacios: un tramo sin dias tambien es informacion —dice que el modelo nunca
    anuncio eso— y omitirlo lo haria parecer inexistente.
    """

    por_banda: dict[str, list[tuple[float, bool]]] = {banda: [] for banda in orden}
    total = 0
    positivos_total = 0
    suma_brier = 0.0

    for probabilidad, ocurrio in pares:
        banda = banda_de(probabilidad)
        por_banda.setdefault(banda, []).append((probabilidad, ocurrio))
        total += 1
        positivos_total += 1 if ocurrio else 0
        suma_brier += (probabilidad - (1.0 if ocurrio else 0.0)) ** 2

    tramos = []
    for banda in orden:
        filas = por_banda.get(banda, [])
        if not filas:
            tramos.append(
                TramoCalibrado(
                    banda=banda,
                    dias=0,
                    episodios=0,
                    anunciado=0.0,
                    observado=0.0,
                    intervalo=(0.0, 1.0),
                )
            )
            continue
        dias = len(filas)
        episodios = sum(1 for _, ocurrio in filas if ocurrio)
        tramos.append(
            TramoCalibrado(
                banda=banda,
                dias=dias,
                episodios=episodios,
                anunciado=sum(probabilidad for probabilidad, _ in filas) / dias,
                observado=episodios / dias,
                intervalo=wilson(episodios, dias),
            )
        )

    return Calibracion(
        tramos=tuple(tramos),
        brier=None if total == 0 else suma_brier / total,
        dias=total,
        episodios=positivos_total,
    )
