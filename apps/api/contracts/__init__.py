"""Punto único de importación del contrato v0.3 para `apps/**`.

El contrato ejecutable vive en `packages/shared` y
H1 lo publicó. Los cinco módulos de este paquete son re-exports de aquel: aquí
no se declara ningún modelo, enum, constante, texto ni entrada del catálogo.

Lo único que este paquete añade son las respuestas de producto que el contrato
publicado todavía no cubre, y lo hace por subclase del modelo de P1, con la
solicitud correspondiente anotada. Están listadas en `README.md`, sección
"Solicitudes a P1".
"""

from __future__ import annotations

from apps.api.contracts import constants, enums, field_catalog, models, texts

__all__ = ["constants", "enums", "field_catalog", "models", "texts"]
