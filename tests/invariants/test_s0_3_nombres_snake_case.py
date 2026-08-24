"""§0.3 — Nombres en inglés snake_case en código/DB/API. Textos de UI en
español, sin excepción."""

import re

from ml.spec_constants import VARIABLE_LABELS_ES, VARIABLE_PROMPTS_ES
from packages.shared.models import DailyLog

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


def test_s0_3_campos_canonicos_son_snake_case_ingles():
    for field in DailyLog.model_fields:
        assert SNAKE_CASE.match(field), f"'{field}' no es snake_case"
        assert field == field.lower()


def test_s0_3_textos_ui_son_espanol():
    # Heurística mínima: los textos de UI usan caracteres/palabras de español
    # (tildes, ñ, signos de interrogación invertidos) y no son snake_case.
    for prompt in VARIABLE_PROMPTS_ES.values():
        assert not SNAKE_CASE.match(prompt)
        assert " " in prompt  # frase, no identificador
    for label in VARIABLE_LABELS_ES.values():
        assert not SNAKE_CASE.match(label)
