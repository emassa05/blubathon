"""Persistencia de Faro. Todo el SQL del proyecto vive aquí (CONVENTIONS 13).

Los módulos exponen comandos y consultas concretos, no un repositorio genérico
sobre cada tabla (CONVENTIONS 20).
"""

from __future__ import annotations

from apps.api.store.db import Database, connect
from apps.api.store.projection import Projection, project_as_of

__all__ = ["Database", "Projection", "connect", "project_as_of"]
