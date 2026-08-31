"""Deja la base lista para probar los dos subsistemas a la vez.

Cada pieza ya existía por separado —`tools.seed`, `tools.demo_history`,
`tools.train`— pero probar el sistema exigía encadenarlas en el orden correcto,
con el conjunto de adaptadores correcto, y sabiendo por qué hace falta cada una.
Encadenarlas mal no falla: deja una demo a medias que parece rota.

Los dos subsistemas piden cosas distintas, y esa es la razón de que el montaje
tenga varios pasos y no uno:

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

Y hay un orden que no se ve en las piezas y solo existe aquí: **quién se siembra
antes del entrenamiento y quién después**. El challenger no se entrena en
runtime, se lee del artefacto en `shadow`; un día fabricado antes de que exista
ese artefacto se guarda con el track abstenido para siempre, y lo que queda en
pantalla es la tasa base, que apenas se mueve de un día al siguiente. Sembrando
primero la cohorte y entrenando con ella, los días de los dos niños de la
pantalla nacen ya con la corrección puesta: el mismo niño pasa de ~15% un día
tranquilo a ~56% uno difícil, que es lo que la pantalla promete cuando dice que
la cifra depende del cuestionario.
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

#: Los dos de siempre: los que se abren para mirar la pantalla, y cuyos enlaces
#: andan escritos en cuadernos y en la cabeza de la gente.
#:
#: Se siembran **después** de entrenar, y por eso van aparte. Ver `montar_demo`.
NINOS_DE_LA_PANTALLA: tuple[tuple[str, str, int], ...] = (
    (ids.SUBJECT_REAL, "Niña demo 4", 26),
    (ids.SUBJECT_REAL_B, "Niño demo 5", 30),
)

#: Los seis que hacen medible la **calibración**. Un niño tiene una tasa base y
#: todos sus días caen en el mismo tramo de riesgo, así que con dos parecidos la
#: medida solo cubría uno: 109 de 120 días en `medium`, y los tramos `low` y
#: `high` sin nada con que contrastarse. Repartiendo los días difíciles de 0 a
#: 64, las tasas base salen escalonadas desde ~16% hasta ~69% y los tres tramos
#: se llenan.
#:
#: La cuenta que hay detrás, con la lotería de `demo_history` —70% de crisis en
#: día difícil, 15% en día tranquilo— y 65 días:
#:
#:     tasa base ~= (1 + 9.75 + 0.55 * dificiles) / 67
#:
#: 0 difíciles dan ~16% (tramo bajo), 26 dan ~37% (medio), 64 dan ~69% (alto).
#:
#: Son además los que entrenan al challenger, porque son los primeros en tener
#: historial.
NINOS_DE_LA_COHORTE: tuple[tuple[str, str, int], ...] = (
    (ids.SUBJECT_COHORTE_C, "Niña demo 7", 0),
    (ids.SUBJECT_COHORTE_D, "Niño demo 8", 3),
    (ids.SUBJECT_COHORTE_E, "Niña demo 9", 14),
    (ids.SUBJECT_COHORTE_F, "Niño demo 10", 45),
    (ids.SUBJECT_COHORTE_G, "Niña demo 11", 55),
    (ids.SUBJECT_COHORTE_H, "Niño demo 12", 64),
)

#: A quién se le fabrica historial, en el orden en que se enseña al terminar.
#: Sembrar no sigue este orden; ver `montar_demo`.
NINOS: tuple[tuple[str, str, int], ...] = NINOS_DE_LA_PANTALLA + NINOS_DE_LA_COHORTE

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
    """Siembra, fabrica el historial de la cohorte, entrena, y recién ahí el de
    los dos niños de la pantalla.

    El orden no es negociable por dos motivos distintos. El primero es de
    dependencias: el historial necesita el catálogo y el objetivo ya sembrados,
    y el entrenamiento necesita los resultados verificados que produce el
    historial. El segundo es lo que se ve: el historial que se fabrica antes de
    que exista el modelo se queda con el challenger abstenido, así que los dos
    niños que alguien va a abrir se siembran después, y sus días reaccionan al
    cuestionario que declaran.
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

    sembrados: dict[str, NinoSembrado] = {}

    def sembrar(grupo: tuple[tuple[str, str, int], ...], *, ayer_dificil: bool = False) -> None:
        for child_id, etiqueta, dificiles in grupo:
            # `build_history` abre su propia conexión sobre `BLUBATHON_DB_PATH`,
            # así que la ruta se pasa por el entorno antes de llamar, no por
            # argumento.
            historial = build_history(
                child_id=child_id,
                days=dias,
                dificiles=min(dificiles, dias),
                ayer_dificil=ayer_dificil,
                adapters="real",
            )
            sembrados[child_id] = NinoSembrado(
                child_id=child_id,
                etiqueta=etiqueta,
                dias=len(historial.days),
                verificados=historial.verified,
            )

    # La cohorte primero, y sola: es la que entrena. Son seis sujetos, de sobra
    # para la validación dejando uno fuera, y sus días quedan con el challenger
    # abstenido porque todavía no hay artefacto que leer. Eso no se pierde: la
    # calibración los mide por la tasa base que de verdad se les enseñó.
    sembrar(NINOS_DE_LA_COHORTE)

    informe = train(
        connection,
        tenant_id=DEMO_TENANT_ID,
        target_definition_version=OBJETIVO,
    )
    connection.commit()

    # Y ahora los dos que alguien abre. Con el artefacto ya en `shadow`, cada
    # uno de sus días se estima como se estimaría hoy: tasa base corregida por
    # el cuestionario de ese día. Ninguno de sus desenlaces entró al
    # entrenamiento, así que además son días fuera de muestra.
    #
    # `ayer_dificil`: ayer es el día que se abre al entrar, y se quiere rojo.
    # Con la costumbre de estos dos —difícil el ~40% de los días— un día malo
    # deja la desviación en +0.6 en sueño y en regulación, y con los
    # coeficientes que sale entrenando eso sube la cifra por encima del corte
    # de `alto`. Un día tranquilo la baja a la mitad de la tasa base.
    sembrar(NINOS_DE_LA_PANTALLA, ayer_dificil=True)

    return DemoResult(
        # En el orden en que se enseñan, que no es el orden en que se sembraron.
        ninos=tuple(sembrados[child_id] for child_id, _, _ in NINOS),
        fragmentos=fragmentos,
        modelo=informe.model_version,
        motivo_sin_modelo=informe.reason,
        documentos_locales=documentos,
        omitidos=omitidos,
    )


__all__ = [
    "NINOS",
    "NINOS_DE_LA_COHORTE",
    "NINOS_DE_LA_PANTALLA",
    "OBJETIVO",
    "DemoResult",
    "NinoSembrado",
    "montar_demo",
]
