from ml.narrative.llm import generate_with_llm
from ml.narrative.payload import build_narrative_payload
from ml.narrative.template import render_template


def generate_narrative(payload: dict) -> tuple[dict, str]:
    """SPEC §10.2 — intenta LLM, cae a plantilla. Devuelve (narrative, source)."""
    llm_result = generate_with_llm(payload)
    if llm_result is not None:
        return llm_result, "llm"
    return render_template(payload), "template"


__all__ = ["build_narrative_payload", "generate_narrative", "render_template"]
