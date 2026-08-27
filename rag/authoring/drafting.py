"""The optional local LLM draft (SPEC 9.1, 9.4, CONVENTIONS 11.2).

This step sits at the only place in Faro where a language model is allowed: it
proposes wording for a candidate strategy, offline, from fragments of versioned
literature, and its output cannot reach anybody without an evidence review and
an independent clinical review. Runtime makes zero LLM calls (C29).

The prompt is versioned package data with declared input and output schemas, and
its hash goes into the build manifest, so changing the wording changes the build.
Everything that reaches the transport is checked first: only authorised
literature, never a note, a message or an identifier (SPEC 2.23).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, Final, Protocol, runtime_checkable
from uuid import UUID

from packages.shared.canonical import bytes_hash
from packages.shared.domain.rag import DocumentChunk
from rag.domain.text_guard import assert_literature_only, assert_no_clinical_text, literature

PROMPT_PACKAGE: Final = "rag.authoring.prompts"
AUTHORING_DRAFT_PROMPT_FILE: Final = "authoring_draft.v0_4_0.json"

logger = logging.getLogger("blubathon.rag")


@runtime_checkable
class DraftTransport(Protocol):
    """A local model. Tests use a simulated transport, never a live daemon."""

    @property
    def model_id(self) -> str: ...

    @property
    def model_sha256(self) -> str: ...

    def complete(self, prompt: str) -> str: ...


class DraftUnavailableError(RuntimeError):
    """No registered local model, so there is no draft. Authoring stays manual."""


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """A versioned prompt with its declared schemas and its own hash."""

    prompt_version: str
    template: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    prompt_sha256: str

    def render(self, *, generalized_question_es: str, fragments: str) -> str:
        return self.template.format(
            generalized_question_es=generalized_question_es, fragments=fragments
        )


@lru_cache(maxsize=1)
def load_prompt() -> PromptTemplate:
    """Read the authoring prompt from package data and hash its exact bytes."""

    raw = resources.files(PROMPT_PACKAGE).joinpath(AUTHORING_DRAFT_PROMPT_FILE).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return PromptTemplate(
        prompt_version=payload["prompt_version"],
        template="\n".join(payload["template"]),
        input_schema=payload["input_schema"],
        output_schema=payload["output_schema"],
        prompt_sha256=bytes_hash(raw),
    )


@dataclass(frozen=True, slots=True)
class DraftRequest:
    """A generalised question and the fragments a draft may quote from."""

    generalized_question_es: str
    chunks: tuple[DocumentChunk, ...]


@dataclass(frozen=True, slots=True)
class DraftResult:
    """What the model returned, plus what produced it. Still only a draft."""

    prompt_version: str
    prompt_sha256: str
    model_id: str
    model_sha256: str
    rendered_prompt: str
    raw_output: str

    def payload(self) -> dict[str, Any]:
        """The model output parsed as JSON, or a refusal it is not usable."""

        try:
            return json.loads(self.raw_output)
        except json.JSONDecodeError as error:
            raise ValueError("the local draft is not valid JSON and cannot be reviewed") from error


def render_fragments(chunks: Iterable[DocumentChunk]) -> str:
    """Fragments in a stable, quotable form. Nothing but literature goes in."""

    lines = [
        f"[{chunk.document_version_id} | {chunk.locator}]\n{chunk.text}"
        for chunk in sorted(chunks, key=lambda item: item.chunk_sha256)
    ]
    return "\n\n".join(lines)


def request_draft(
    request: DraftRequest,
    *,
    transport: DraftTransport | None,
    authorised_document_version_ids: frozenset[UUID],
    clinical_sentinels: Sequence[str] = (),
) -> DraftResult:
    """Draft a candidate strategy locally, after auditing everything it sees."""

    if transport is None:
        logger.warning("draft abortado motivo=transport_no_registrado")
        raise DraftUnavailableError(
            "no local model is registered with a licence, model card and artifact hash; "
            "authoring stays manual (TAREAS 13)"
        )
    if not request.chunks:
        raise ValueError("a draft is grounded in at least one retrieved fragment")

    assert_literature_only(
        (literature(chunk.text, chunk.document_version_id) for chunk in request.chunks),
        authorised=authorised_document_version_ids,
    )

    prompt = load_prompt()
    rendered = prompt.render(
        generalized_question_es=request.generalized_question_es,
        fragments=render_fragments(request.chunks),
    )
    assert_no_clinical_text(rendered, sentinels=clinical_sentinels)

    logger.info(
        "draft inicio model=%s prompt_version=%s chunks=%d prompt_chars=%d",
        transport.model_id,
        prompt.prompt_version,
        len(request.chunks),
        len(rendered),
    )
    try:
        raw_output = transport.complete(rendered)
    except Exception:
        logger.exception("draft error model=%s", transport.model_id)
        raise
    logger.info(
        "draft fin model=%s output_chars=%d",
        transport.model_id,
        len(raw_output),
    )

    return DraftResult(
        prompt_version=prompt.prompt_version,
        prompt_sha256=prompt.prompt_sha256,
        model_id=transport.model_id,
        model_sha256=transport.model_sha256,
        rendered_prompt=rendered,
        raw_output=raw_output,
    )
