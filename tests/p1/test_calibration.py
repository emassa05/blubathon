"""La calibracion de la cohorte: lo anunciado contra lo que ocurrio."""

from __future__ import annotations

import pytest

from ml.calibration import calibrar, wilson

ORDEN = ("low", "medium", "high")


def banda_de(probabilidad: float) -> str:
    """Los mismos cortes que usa la aplicacion, escritos aqui para el test."""

    if probabilidad >= 0.5:
        return "high"
    if probabilidad >= 0.2:
        return "medium"
    return "low"


def test_wilson_never_claims_certainty_from_a_run_of_zeros() -> None:
    """Cero de veinte no es "entre 0% y 0%": es "no mas de un 16%"."""

    bajo, alto = wilson(0, 20)
    assert bajo == 0.0
    assert 0.10 < alto < 0.25

    # Y lo mismo del otro lado, que es el tramo que mas importa.
    bajo, alto = wilson(20, 20)
    assert alto == 1.0
    assert 0.75 < bajo < 0.90


def test_wilson_narrows_as_the_days_pile_up() -> None:
    anchos = [wilson(n // 2, n)[1] - wilson(n // 2, n)[0] for n in (20, 100, 400)]
    assert anchos[0] > anchos[1] > anchos[2]
    # 400 dias al 50% dan del orden de +-5 puntos.
    assert anchos[2] == pytest.approx(0.098, abs=0.01)


def test_wilson_without_days_admits_everything() -> None:
    assert wilson(0, 0) == (0.0, 1.0)


def test_a_calibrated_model_lands_inside_its_own_interval() -> None:
    """Anuncia 30% en el tramo medio y ocurre el 30%: concuerda."""

    pares = [(0.30, indice % 10 < 3) for indice in range(200)]
    calibracion = calibrar(pares, banda_de=banda_de, orden=ORDEN)

    medio = next(tramo for tramo in calibracion.tramos if tramo.banda == "medium")
    assert medio.dias == 200
    assert medio.episodios == 60
    assert medio.anunciado == pytest.approx(0.30)
    assert medio.observado == pytest.approx(0.30)
    assert medio.concuerda


def test_a_model_that_underestimates_is_caught_by_the_interval() -> None:
    """Anuncia 30% y ocurre el 80%: el intervalo no lo cubre, y eso es el hallazgo."""

    pares = [(0.30, indice % 10 < 8) for indice in range(200)]
    calibracion = calibrar(pares, banda_de=banda_de, orden=ORDEN)

    medio = next(tramo for tramo in calibracion.tramos if tramo.banda == "medium")
    assert medio.observado == pytest.approx(0.80)
    assert not medio.concuerda
    assert medio.intervalo[0] > 0.30


def test_few_days_do_not_catch_anything_and_that_is_the_point() -> None:
    """Con ocho dias el intervalo es tan ancho que no desmiente nada.

    Concordar no confirma. Es justo lo que separa "esta medido" de "hay pocos
    dias todavia", y por eso el numero de dias viaja al lado del intervalo.
    """

    # Anuncia 30% y ocurre el 50%: con 200 dias eso se habria cazado.
    pares = [(0.30, indice % 2 == 0) for indice in range(8)]
    calibracion = calibrar(pares, banda_de=banda_de, orden=ORDEN)

    medio = next(tramo for tramo in calibracion.tramos if tramo.banda == "medium")
    assert medio.dias == 8
    assert medio.observado == pytest.approx(0.50)
    assert medio.concuerda  # con 8 dias, un error de 20 puntos no se desmiente
    assert medio.intervalo[1] - medio.intervalo[0] > 0.4

    # Los mismos 50% contra 30%, con 200 dias: ahora si.
    muchos = calibrar([(0.30, i % 2 == 0) for i in range(200)], banda_de=banda_de, orden=ORDEN)
    assert not next(t for t in muchos.tramos if t.banda == "medium").concuerda


def test_every_band_is_reported_even_when_it_never_fired() -> None:
    """Un tramo vacio dice que el modelo nunca anuncio eso, y se enseña."""

    calibracion = calibrar([(0.30, True)], banda_de=banda_de, orden=ORDEN)

    assert [tramo.banda for tramo in calibracion.tramos] == list(ORDEN)
    alto = next(tramo for tramo in calibracion.tramos if tramo.banda == "high")
    assert alto.dias == 0
    assert alto.intervalo == (0.0, 1.0)


def test_the_bands_split_by_the_announced_number() -> None:
    pares = [(0.10, False), (0.30, True), (0.70, True), (0.80, False)]
    calibracion = calibrar(pares, banda_de=banda_de, orden=ORDEN)

    assert [tramo.dias for tramo in calibracion.tramos] == [1, 1, 2]
    alto = calibracion.tramos[2]
    assert alto.anunciado == pytest.approx(0.75)
    assert alto.observado == pytest.approx(0.5)


def test_the_brier_uses_every_day_once_without_splitting_them() -> None:
    """Por eso dice algo mucho antes de que los tramos se llenen."""

    calibracion = calibrar([(0.0, False), (1.0, True)], banda_de=banda_de, orden=ORDEN)
    assert calibracion.brier == pytest.approx(0.0)

    peor = calibrar([(0.0, True), (1.0, False)], banda_de=banda_de, orden=ORDEN)
    assert peor.brier == pytest.approx(1.0)


def test_no_days_is_not_a_brier_of_zero() -> None:
    vacia = calibrar([], banda_de=banda_de, orden=ORDEN)
    assert vacia.brier is None
    assert not vacia.hay_datos
    assert vacia.dias == 0
