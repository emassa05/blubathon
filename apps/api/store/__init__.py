"""Persistencia de Blubathon. Todo el SQL del proyecto vive aquí.

Los módulos exponen comandos y consultas concretos, no un repositorio genérico
sobre cada tabla.
"""

from __future__ import annotations

from apps.api.store.db import Database, connect
from apps.api.store.projection import Projection, project_as_of

__all__ = ["Database", "Projection", "connect", "project_as_of"]
