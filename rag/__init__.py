"""Offline authoring and deterministic runtime for the clinical catalogue (SPEC 9).

The RAG works at authoring time, not on every clinical query. `rag/domain` holds
what a document, chunk, citation, review and activation gate mean; `rag/authoring`
retrieves and verifies; `rag/runtime` matches a categorical scenario against a
precomputed catalogue and never calls an LLM, an embedding model or a store.

`rag` imports `packages/shared` and nothing else from the repository: it never
reaches the clinical database, and it never sees a subject, a note or an
identifier (CONVENTIONS 4, SPEC 2.23).
"""
