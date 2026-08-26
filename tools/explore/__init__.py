"""Análisis exploratorio. No es parte del sistema en producción.

Nada de acá alimenta una predicción expuesta ni entra al catálogo de tracks.
El challenger de `ml/prediction` es preregistrado: sus dos predictores se
eligieron antes de mirar los datos, y eso es lo que hace honesto su Brier
out-of-fold. Un bosque que revisa las 19 variables y devuelve un ranking hace
lo contrario —elige mirando— así que su salida es una pista sobre dónde buscar,
nunca una afirmación sobre qué predice.

Por eso este paquete vive fuera de `ml/` y sólo escribe reportes.
"""

from __future__ import annotations

from tools.explore.features import FeatureMatrix, build_matrix
from tools.explore.forest import StabilityReport, importance_stability

__all__ = ["FeatureMatrix", "StabilityReport", "build_matrix", "importance_stability"]
