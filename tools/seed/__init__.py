"""Siembra de la demo local con datos completamente ficticios.

`python -m tools.seed --catalog blocked` deja el estado honesto de release: hay
corpus y estrategias revisadas por evidencia, no hay revisor clínico autorizado,
el catálogo no se activa y el runtime demuestra `clinical_review_unavailable`.

`python -m tools.seed --catalog fixture-active` añade un catálogo **fixture**
activado por revisores ficticios, para poder recorrer el flujo profesional
completo en la demo y en los tests. Ese estado no afirma que exista un catálogo
clínicamente activo: los documentos llevan `publisher=FIXTURE_DEMO` y
`rights_basis=fixture_demo_only`.
"""

from __future__ import annotations

from tools.seed.seeder import SeedResult, seed

__all__ = ["SeedResult", "seed"]
