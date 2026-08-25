"""Adaptadores reales sobre las façades de P1.

Este archivo es el punto exacto donde se integra cada artefacto de P1. Hoy
ninguna de las façades del SPEC v0.3 existe todavía en `ml/` ni en `rag/`, así
que el conjunto real falla con un mensaje explícito en vez de fingir un
resultado. Sustituir un mock consiste en implementar aquí la clase equivalente y
borrar su entrada de `MISSING_FACADES`.
"""

from __future__ import annotations

from apps.api.adapters import Ports

# Façades declaradas en TAREAS P1.3-P1.7 que este adaptador necesita.
MISSING_FACADES: tuple[str, ...] = (
    "ml.defaults.assign_audit_mode",
    "ml.defaults.compute_default_decision",
    "ml.form.build_form_plan",
    "ml.form.build_scenario",
    "ml.prediction.predict",
    "rag.runtime.recommend",
)


class P1FacadesUnavailable(RuntimeError):
    """P1 todavía no publicó el contrato ejecutable H1."""


def build_real_ports() -> Ports:
    missing = ", ".join(MISSING_FACADES)
    raise P1FacadesUnavailable("FARO_P1_ADAPTERS=real exige las façades de P1; faltan: " + missing)
