"""Si lo que la cifra anuncia acaba pasando, medido sobre la cohorte."""

from __future__ import annotations

import sqlite3

from apps.api.contracts.models import CalibrationBand, CalibrationResponse
from apps.api.services.base import Services
from apps.api.services.recommendation_query import risk_band_for
from apps.api.store import history
from ml.calibration import calibrar
from packages.shared.texts import CALIBRATION_CAVEAT_ES

#: El orden en que se leen los tramos, de menos a mas riesgo. Los nombres son los
#: que ya produce `risk_band_for`; aqui solo se ordenan.
ORDEN_BANDAS: tuple[str, ...] = ("low", "medium", "high")


class CalibrationService:
    def __init__(self, services: Services) -> None:
        self._services = services

    def cohort(self, connection: sqlite3.Connection, *, tenant_id: str) -> CalibrationResponse:
        """Los tramos de la organizacion, con su intervalo de Wilson.

        `risk_band_for` es la misma funcion que decide la banda de una
        recomendacion, y entra por parametro en vez de reescribirse dentro de
        `ml`: los umbrales son de la aplicacion, y dos definiciones de "riesgo
        alto" se separan sin que nadie lo note.
        """

        pares = [
            (float(fila["probability"]), fila["outcome_status"] == "yes")
            for fila in history.resolved_predictions(connection, tenant_id=tenant_id)
        ]
        calibracion = calibrar(pares, banda_de=risk_band_for, orden=ORDEN_BANDAS)

        return CalibrationResponse(
            bands=tuple(
                CalibrationBand(
                    band=tramo.banda,
                    days=tramo.dias,
                    episodes=tramo.episodios,
                    announced=tramo.anunciado,
                    observed=tramo.observado,
                    interval=tramo.intervalo,
                )
                for tramo in calibracion.tramos
            ),
            brier=calibracion.brier,
            days=calibracion.dias,
            episodes=calibracion.episodios,
            caveat_es=CALIBRATION_CAVEAT_ES,
        )
