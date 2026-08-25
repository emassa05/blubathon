"""The deterministic runtime: a pure decision, never a call (SPEC 9.8).

This package imports `packages/shared` and the standard library. It has no
dependency on `rag/authoring`, on any model, index, HTTP client or database, and
the import contract in `.importlinter` is what proves it rather than this
sentence.
"""

from rag.runtime.decide import RuntimeCatalog, RuntimeInputs, decide

__all__ = ["RuntimeCatalog", "RuntimeInputs", "decide"]
