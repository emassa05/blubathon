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
from tools.rag_authoring.load_local import load_local_corpus
from tools.seed import ids
from tools.seed.seeder import seed
from tools.train.run import train

#: A quién se le fabrica historial, y con cuántos días de mal perfil.
#:
#: Los dos primeros son los de siempre y no se tocan: son los que se abren para
#: mirar la pantalla, y sus enlaces andan escritos en cuadernos y en la cabeza de
#: la gente.
#:
#: Los seis siguientes existen para que la **calibración** se pueda comprobar. Un
#: niño tiene una tasa base y todos sus días caen en el mismo tramo de riesgo, así
#: que con dos parecidos la medida solo cubría uno: 109 de 120 días en `medium`,
#: y los tramos `low` y `high` sin nada con que contrastarse. Repartiendo los días
#: difíciles de 0 a 64, las tasas base salen escalonadas desde ~16% hasta ~69% y
#: los tres tramos se llenan.
#:
#: La cuenta que hay detrás, con la lotería de `demo_history` —70% de crisis en
#: día difícil, 15% en día tranquilo— y 65 días:
#:
#:     tasa base ~= (1 + 9.75 + 0.55 * dificiles) / 67
#:
#: 0 difíciles dan ~16% (tramo bajo), 26 dan ~37% (medio), 64 dan ~69% (alto).
NINOS: tuple[tuple[str, str, int], ...] = (
    (ids.SUBJECT_REAL, "Niña demo 4", 26),
    (ids.SUBJECT_REAL_B, "Niño demo 5", 30),
    (ids.SUBJECT_COHORTE_C, "Niña demo 7", 0),
    (ids.SUBJECT_COHORTE_D, "Niño demo 8", 3),
    (ids.SUBJECT_COHORTE_E, "Niña demo 9", 14),
    (ids.SUBJECT_COHORTE_F, "Niño demo 10", 45),
    (ids.SUBJECT_COHORTE_G, "Niña demo 11", 55),
    (ids.SUBJECT_COHORTE_H, "Niño demo 12", 64),
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
    #: Documentos de `data/local_corpus/` cargados en este montaje.
    documentos_locales: int = 0
    #: Archivos de ese directorio que no se pudieron cargar, con su motivo.
    omitidos: tuple[str, ...] = ()

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

    # El corpus sembrado son fragmentos ficticios cortos, suficientes para que
    # la recuperación case pero no para juzgar cómo redacta el modelo. Si hay
    # documentos en `data/local_corpus/`, entran acá: así un `--reset` no
    # obliga a recargarlos a mano. Sin ese directorio esto no hace nada.
    documentos, _, omitidos = load_local_corpus(connection)
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
        documentos_locales=documentos,
        omitidos=omitidos,
    )


__all__ = ["NINOS", "OBJETIVO", "DemoResult", "NinoSembrado", "montar_demo"]
