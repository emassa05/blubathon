"""Adaptadores reales sobre el dominio publicado por P1.

`FARO_P1_ADAPTERS=real` selecciona este conjunto. Cada clase traduce entre el
puerto de P2 y la API que P1 publica de verdad; la traducción vive aquí, y ni
los puertos ni los servicios ni el store cambian de forma para acomodarla.

Correspondencia con lo que P2 esperaba antes de la integración:

- `ml.defaults.assign_audit_mode`: existe con la misma intención; cambia la
  forma de `AuditAssignment`.
- `ml.defaults.compute_default_decision`: existe, y opera sobre la ventana que
  `eligible_history` construye a partir de filas ya cargadas.
- `ml.form.build_form_plan`: existe, y recibe la cobertura que `compute_dqi`
  calcula, no un `coverage` inventado.
- `ml.form.build_scenario`: existe, con `ScenarioInputs` y una sesión enviada.
- `ml.prediction.predict`: **no existe**. P1 publica el doble track separado, y
  el adaptador llama a `score_simulation`, `build_personal_baseline` y
  `assess_trainability` y arma la tupla de salidas.
- `rag.runtime.recommend`: **no existe**. P1 publica `decide(RuntimeInputs)` con
  `RuntimeCatalog`, y el adaptador arma esas entradas desde el store.

Las dos últimas son las que el adaptador construye; el resto es traducción de
nombres y de tipos.
"""

from __future__ import annotations

from apps.api.adapters import Ports
from apps.api.adapters.p1.defaults import P1Defaults
from apps.api.adapters.p1.form import P1Form
from apps.api.adapters.p1.prediction import P1Prediction
from apps.api.adapters.p1.rag import P1RagRuntime
from apps.api.store.db import Database

REAL_SOURCE = "p1"

# Ninguna façade queda sin cablear. Lo que sigue sin poder producir un número no
# es una façade que falte, sino un artefacto que el repositorio no contiene: el
# binario de simulación v0.2 está fuera de Git y el track responde `unavailable`
# con `model_artifact_unavailable`, que es la respuesta correcta (SPEC 8.5).
MISSING_FACADES: tuple[str, ...] = ()


class P1FacadesUnavailable(RuntimeError):
    """El conjunto real exige una base: el dominio puro opera sobre filas."""


def build_real_ports(
    *, database: Database | None = None, secret: bytes = b"faro-demo-audit-secret"
) -> Ports:
    if database is None:
        raise P1FacadesUnavailable(
            "FARO_P1_ADAPTERS=real necesita la base: `ml` y `rag` son funciones puras "
            "sobre filas ya cargadas y el adaptador es quien las carga"
        )
    return Ports(
        defaults=P1Defaults(database=database, secret=secret),
        form=P1Form(database=database, secret=secret),
        prediction=P1Prediction(database=database),
        rag=P1RagRuntime(database=database, secret=secret),
        source=REAL_SOURCE,
    )
