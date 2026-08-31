"""Transportes de redacción: API de Claude o un modelo local.

`rag/authoring/drafting.py` declara el protocolo `DraftTransport`; esto lo
implementa. Es el único punto del sistema que habla con un LLM, y solo recibe
los fragmentos ya recuperados (nunca identidad, notas ni texto libre): quien
audita eso es `request_draft`, antes de llamar acá.

El esquema de salida sale del prompt versionado, así que la respuesta no puede
desviarse de la forma que `verify_citation` espera. `parafrasis_es` es una
paráfrasis y no se verifica contra el fragmento; lo que sí se verifica aguas
abajo es la procedencia declarada (`source_fragment`), que debe apuntar a un
fragmento realmente recuperado.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Final

logger = logging.getLogger("blubathon.rag")

MODEL_ID: Final = "claude-opus-5"
MAX_TOKENS: Final = 8192

OLLAMA_URL: Final = "http://127.0.0.1:11434"
OLLAMA_MODEL: Final = "qwen2.5:7b-instruct"
# Un modelo local en CPU puede tardar minutos en un prompt con varios
# fragmentos; el default de urllib (sin límite) colgaría la BackgroundTask.
OLLAMA_TIMEOUT_SECONDS: Final = 300
# Respuestas parafraseadas y desarrolladas necesitan más espacio que el default
# de Ollama (128 tokens), que cortaría el JSON a la mitad.
OLLAMA_NUM_PREDICT: Final = 2048

_ATTRIBUTION_RULE: Final = (
    "Redacta con tus propias palabras: `parafrasis_es` reescribe la idea del "
    "fragmento, nunca la copia. En cambio `source_fragment` es el número de la etiqueta "
    "[fragmento N] del fragmento del que sacaste la idea, como entero. Citar un "
    "número que no aparece entre los fragmentos entregados invalida el borrador "
    "completo."
)


class AnthropicDraftTransport:
    """`DraftTransport` sobre la API de Claude.

    `model_sha256` no es el hash de los pesos —un modelo servido por API no
    expone ninguno—: es el identificador de la versión servida, que es lo que
    de verdad fija este borrador y lo que se guarda en el manifiesto.
    """

    def __init__(self, *, api_key: str | None = None, model: str = MODEL_ID) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._model = model
        self._output_schema = _output_schema()

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def model_sha256(self) -> str:
        return f"api-served:{self._model}"

    def complete(self, prompt: str) -> str:
        started = time.monotonic()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=_ATTRIBUTION_RULE,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": self._output_schema}},
        )
        elapsed = time.monotonic() - started
        if response.stop_reason == "refusal":
            logger.warning("anthropic refusal model=%s elapsed_s=%.2f", self._model, elapsed)
            raise DraftRefusedError("el modelo declinó redactar este borrador")
        logger.info("anthropic completado model=%s elapsed_s=%.2f", self._model, elapsed)
        return next(block.text for block in response.content if block.type == "text")


class DraftRefusedError(RuntimeError):
    """El modelo declinó. No hay borrador y la recomendación se abstiene."""


class OllamaDraftTransport:
    """`DraftTransport` sobre un modelo servido por Ollama, en la misma máquina.

    Nada del prompt sale de la red local. `model_sha256` es el digest real que
    Ollama reporta para el modelo cargado, así que acá la procedencia es más
    fuerte que contra una API: identifica los pesos exactos que redactaron.

    Advertencia práctica: lo que un modelo chico falla acá no es parafrasear
    —eso ahora se espera— sino declarar bien la procedencia. Si abstiene siempre
    con `draft_not_grounded`, revisá qué `source_fragment` está devolviendo
    antes de tocar nada más.
    """

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_URL,
        timeout: int = OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._output_schema = _output_schema()
        self._digest: str | None = None

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def model_sha256(self) -> str:
        if self._digest is None:
            self._digest = self._resolve_digest()
        return self._digest

    def _resolve_digest(self) -> str:
        """El digest que Ollama publica para el modelo, o una marca de ausencia.

        `/api/show` no trae `digest` propio; `/api/tags` sí, por modelo
        cargado. Un digest que no se pudo leer no puede inventarse: el
        manifiesto diría que este borrador salió de unos pesos que nadie
        verificó.
        """

        try:
            request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                listing = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError):
            return f"ollama-digest-unavailable:{self._model}"
        for model in listing.get("models", []):
            if model.get("name") == self._model or model.get("model") == self._model:
                digest = model.get("digest")
                if digest:
                    return str(digest)
        return f"ollama-digest-unavailable:{self._model}"

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "format": self._output_schema,
            "options": {"temperature": 0, "num_predict": OLLAMA_NUM_PREDICT},
            "messages": [
                {"role": "system", "content": _ATTRIBUTION_RULE},
                {"role": "user", "content": prompt},
            ],
        }
        logger.info("ollama request model=%s base_url=%s", self._model, self._base_url)
        started = time.monotonic()
        try:
            body = self._post_json("/api/chat", payload)
        except (urllib.error.URLError, TimeoutError):
            logger.exception(
                "ollama error model=%s elapsed_s=%.2f", self._model, time.monotonic() - started
            )
            raise
        elapsed = time.monotonic() - started
        content = body.get("message", {}).get("content", "")
        if not content.strip():
            logger.warning("ollama respuesta vacía model=%s elapsed_s=%.2f", self._model, elapsed)
            raise DraftRefusedError(f"{self._model} devolvió una respuesta vacía")
        logger.info(
            "ollama completado model=%s elapsed_s=%.2f output_chars=%d",
            self._model,
            elapsed,
            len(content),
        )
        return content

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _output_schema() -> dict[str, Any]:
    from rag.authoring.drafting import load_prompt

    schema = json.loads(json.dumps(load_prompt().output_schema))
    _require_all(schema)
    return schema


def _require_all(node: Any) -> None:
    """`json_schema` exige `required` y `additionalProperties: false` completos."""

    if not isinstance(node, dict):
        return
    if node.get("type") == "object":
        properties = node.get("properties", {})
        node["required"] = list(properties)
        node["additionalProperties"] = False
        for child in properties.values():
            _require_all(child)
    if node.get("type") == "array":
        _require_all(node.get("items"))
