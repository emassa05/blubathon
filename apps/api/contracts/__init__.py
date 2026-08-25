"""Contrato de la API v0.3 consumido por `apps/api` y por `apps/web`.

PUERTO HACIA P1 - LEER ANTES DE MODIFICAR
=========================================

`CONVENTIONS 6` y `TAREAS 2` asignan el contrato ejecutable a P1, en
`packages/shared`. En el momento de escribir este paquete, `packages/shared`
todavía contiene el contrato v0.2 (que además importa `ml.spec_constants`, cosa
que el SPEC v0.3 prohíbe), y P1 aún no ha publicado H1.

P2 necesita modelos de request/response para construir rutas, servicios,
persistencia y frontend en paralelo. Este paquete es esa dependencia **aislada
detrás de un único punto de sustitución**:

- No es un contrato compartido alternativo: solo lo importa `apps/**`.
- No se copia a `packages/shared` ni se publica como schema.
- Cuando P1 publique H1, cada módulo de aquí pasa a ser un re-export de
  `packages.shared`, y ninguna ruta, servicio, store o componente cambia.

Divergencias conocidas que P2 debe reportar a P1 con request, response y test
consumidor literal están listadas en `README.md`, sección "Solicitudes a P1".
"""

from __future__ import annotations

from apps.api.contracts import constants, enums, field_catalog, models, texts

__all__ = ["constants", "enums", "field_catalog", "models", "texts"]
