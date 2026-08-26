"""Análisis exploratorio. No es parte del sistema en producción.

La herramienta principal es una tabla de frecuencias: se agrupan los días por el
valor que tuvo cada variable y se cuenta cuántos terminaron en crisis. Es
aritmética, se lee sin saber estadística y se puede rehacer a mano.

Lo que hace confiable esa tabla no es el método sino cómo se arma la matriz:
cada día se alinea con la observación de su fecha local —no la del día UTC
siguiente, que ya cae dentro de la ventana que se quiere predecir—, las
variables registradas sólo algunos días se descartan enteras en vez de recortar
la muestra en silencio, y las que nunca cambian dentro de un mismo niño quedan
fuera porque no pueden explicar por qué un día terminó distinto del anterior.

`--bosque` corre además un bosque aleatorio. Responde una pregunta más dura
—si la variable ayuda a predecir a un niño que el modelo nunca vio— y con siete
eventos la respuesta es que no, ninguna. Vale como control, no como titular.

Nada de acá alimenta una predicción expuesta. El challenger de `ml/prediction`
es preregistrado: sus dos predictores se eligieron antes de mirar los datos, y
eso es lo que hace honesto su Brier fuera de muestra. Este paquete elige
mirando, así que su salida es una pista sobre dónde buscar, nunca una afirmación
sobre qué predice. Por eso vive fuera de `ml/` y sólo escribe reportes.
"""

from __future__ import annotations

from tools.explore.features import FeatureMatrix, build_matrix
from tools.explore.forest import StabilityReport, importance_stability
from tools.explore.tables import FrequencyReport, VariableTable, build_tables

__all__ = [
    "FeatureMatrix",
    "FrequencyReport",
    "StabilityReport",
    "VariableTable",
    "build_matrix",
    "build_tables",
    "importance_stability",
]
