"""Importación del conjunto NeuroHack 2026 al camino de ingesta del esquema.

Los CSV del desafío son observaciones ya recogidas fuera de la plataforma, así
que entran por el único camino que el esquema define para eso: `source_mappings`
aprobado, `entry_mode='imported_observed'`, `intake_channel='import'`. No es una
siembra —`tools.seed` sigue siendo ficticio (CONVENTIONS 15)— y por eso vive en
su propio paquete y nunca escribe en `packages/shared/examples`.

El mapeo de valores es total y explícito: un valor de CSV que no esté en las
tablas de `mapping.py` detiene la importación en vez de degradarse a `other`,
porque una categoría inventada en silencio contamina el baseline.
"""

from __future__ import annotations

from tools.import_hackathon.importer import ImportReport, import_dataset
from tools.import_hackathon.loader import Dataset, load_dataset

__all__ = ["Dataset", "ImportReport", "import_dataset", "load_dataset"]
