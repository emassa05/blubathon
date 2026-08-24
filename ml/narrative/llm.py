"""LLM local (Ollama, 3B) — SPEC §10.1, §10.2, §10.3.

El LLM SOLO redacta (§0.1). Si Ollama no está disponible, o la salida no
valida contra el schema tras un reintento, cae a la plantilla determinista.
Ese fallback es obligatorio y se prueba explícitamente (§10.2).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ml.spec_constants import LLM_MAX_ACTIONS, LLM_MAX_RETRIES, LLM_TEMPERATURE, STRATEGIES

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b-instruct"
OLLAMA_TIMEOUT_S = 4

_SYSTEM_PROMPT_PATH = __file__.replace("llm.py", "prompts/narrative_v1.md")


def _system_prompt() -> str:
    with open(_SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _valid_actions(actions_es: list, allowed_labels: set[str]) -> bool:
    return (
        isinstance(actions_es, list)
        and 0 <= len(actions_es) <= LLM_MAX_ACTIONS
        and all(isinstance(a, str) and a in allowed_labels for a in actions_es)
    )


def _validate_schema(obj: dict, payload: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    if not all(k in obj for k in ("headline_es", "explanation_es", "actions_es")):
        return False
    if not isinstance(obj["headline_es"], str) or not isinstance(obj["explanation_es"], str):
        return False
    if len(obj["explanation_es"].split()) > 60:
        return False
    allowed_labels = {STRATEGIES[sid] for sid in payload["candidate_strategies"]}
    return _valid_actions(obj["actions_es"], allowed_labels)


def _call_ollama(payload: dict) -> dict | None:
    prompt = (
        "Devuelve SOLO un JSON con headline_es, explanation_es (<=60 palabras) "
        "y actions_es (<=3, tomadas literalmente de candidate_strategies.label_es). "
        f"NarrativePayload: {json.dumps(payload, ensure_ascii=False)}"
    )
    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": _system_prompt(),
            "format": "json",
            "stream": False,
            "options": {"temperature": LLM_TEMPERATURE},
        }
    ).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_S) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return json.loads(raw["response"])
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError):
        return None


def generate_with_llm(payload: dict) -> dict | None:
    """Intenta LLM, reintenta una vez si no valida. `None` -> el caller cae
    a la plantilla determinista (§10.2)."""
    for _ in range(LLM_MAX_RETRIES + 1):
        result = _call_ollama(payload)
        if result is not None and _validate_schema(result, payload):
            return result
    return None
