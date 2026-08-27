"""Deja la base lista para probar los dos subsistemas a la vez.

Cada pieza ya existía por separado —`tools.seed`, `tools.demo_history`,
`tools.train`— pero probar el sistema exigía encadenarlas en el orden correcto,
con el conjunto de adaptadores correcto, y sabiendo por qué hace falta cada una.
Encadenarlas mal no falla: deja una demo a medias que parece rota.

Los dos subsistemas piden cosas distintas, y esta es la razón de que el montaje
tenga tres pasos y no uno:

  Recomendación (RAG)
      Necesita un corpus con el vocabulario que generan las consultas. Se siembra
      con la base: `query_for()` arma la consulta desde las etiquetas del
      catálogo, así que un corpus que no las repita deja al sistema abstenido en
      `no_indexed_match`. Redactar el texto necesita además un modelo de lenguaje
      (`BLUBATHON_DRAFT_LLM`); sin él la abstención es `draft_unavailable`, que
      es correcta y no un fallo del montaje.

  Porcentaje de riesgo
      Necesita cinco resultados verificados por niño, y cada uno tarda 24 h
      reales en poder confirmarse: por la aplicación harían falta cinco días de
      calendario. `tools.demo_history` los fabrica hacia atrás.
      Y para que la cifra reaccione al cuestionario del día hace falta el
      challenger entrenado, que exige **dos** sujetos: se valida dejando uno
      fuera, y con uno solo no queda nada con qué entrenar.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from apps.api.context import DEMO_TENANT_ID
from tools.demo_history import build_history
from tools.seed import ids
from tools.seed.seeder import seed
from tools.train.run import train

#: Los dos sujetos de cohorte real. Son los únicos sobre los que el baseline
#: puede estimar: `_origin_for` marca `synthetic` toda la cohorte de fixture, y
#: el modelo descarta lo sintético (SPEC 8.5).
NINOS: tuple[tuple[str, str, int], ...] = (
    (ids.SUBJECT_REAL, "Niña demo 4", 26),
    (ids.SUBJECT_REAL_B, "Niño demo 5", 30),
)

#: Objetivo con alcance de organización, el que exige un sujeto real.
OBJETIVO = ids.TARGET_TENANT_A

DIAS_POR_DEFECTO = 65


@dataclass(frozen=True, slots=True)
class NinoSembrado:
    child_id: str
    etiqueta: str
    dias: int
    verificados: int


@dataclass(frozen=True, slots=True)
class DemoResult:
    ninos: tuple[NinoSembrado, ...]
    fragmentos: int
    modelo: str | None
    motivo_sin_modelo: str | None

    @property
    def entrenado(self) -> bool:
        return self.modelo is not None


def montar_demo(
    connection: sqlite3.Connection,
    *,
    dias: int = DIAS_POR_DEFECTO,
    db_path: str | None = None,
) -> DemoResult:
    """Siembra, fabrica el historial y entrena, en ese orden.

    El orden no es negociable: el historial necesita el catálogo y el objetivo
    ya sembrados, y el entrenamiento necesita los resultados verificados que
    produce el historial.
    """

    # `fixture-active` y no `blocked`: con el catálogo bloqueado el runtime se
    # abstiene con `clinical_review_unavailable` y no hay cuestionario que
    # recorrer.
    #
    # Sin `now`: la semilla usa su época fija, y con ella el perfil del sujeto
    # queda vigente desde 2025-12-31. Pasarle el reloj de hoy lo dejaría vigente
    # desde ayer, y entonces el historial fabricado hacia atrás cae fuera de su
    # vigencia: los episodios nacen sin `care_mode` y el dominio los rechaza al
    # releerlos.
    seed(connection, catalog_profile="fixture-active")
    connection.commit()

    fragmentos = connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]

    sembrados = []
    for child_id, etiqueta, dificiles in NINOS:
        # `build_history` abre su propia conexión sobre `BLUBATHON_DB_PATH`, así
        # que la ruta se pasa por el entorno antes de llamar, no por argumento.
        historial = build_history(
            child_id=child_id,
            days=dias,
            dificiles=min(dificiles, dias),
            adapters="real",
        )
        sembrados.append(
            NinoSembrado(
                child_id=child_id,
                etiqueta=etiqueta,
                dias=len(historial.days),
                verificados=historial.verified,
            )
        )

    informe = train(
        connection,
        tenant_id=DEMO_TENANT_ID,
        target_definition_version=OBJETIVO,
    )
    connection.commit()

    return DemoResult(
        ninos=tuple(sembrados),
        fragmentos=fragmentos,
        modelo=informe.model_version,
        motivo_sin_modelo=informe.reason,
    )


__all__ = ["NINOS", "OBJETIVO", "DemoResult", "NinoSembrado", "montar_demo"]
