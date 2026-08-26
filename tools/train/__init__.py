"""Entrenamiento offline del challenger.

Es el comando que el adaptador de predicción ya esperaba: sin una versión en
estado `shadow`, `_challenger` responde `model_state_not_shadow`, que es
literalmente «nadie entrenó todavía».

Acá no hay machine learning nuevo. El ajuste es el que ya vive en
`ml/prediction/challenger.py` —una regresión logística de dos variables sobre la
tasa base personal, con su lambda elegido por validación dejando un niño
afuera—. Lo que agrega este paquete es la parte de ingeniería de datos: fijar el
conjunto sobre el que se entrenó, dejar registro del intento haya salido bien o
mal, publicar el artefacto con su huella y guardar la evaluación junto a sus
limitaciones.

Eso es lo que hace que el modelo sea una base y no un experimento: mañana se
puede cambiar el ajuste por otro mejor y las cuatro tablas siguen diciendo sobre
qué datos se entrenó, quién lo corrió y cuánto midió.

Nada de acá promueve un modelo a producción. El challenger se queda en sombra.
"""

from __future__ import annotations

from tools.train.dataset import TrainingDataset, build_dataset
from tools.train.run import TrainingReport, train

__all__ = ["TrainingDataset", "TrainingReport", "build_dataset", "train"]
