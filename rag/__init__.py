"""Offline authoring for the clinical catalogue.

The RAG works at authoring time, not on every clinical query. `rag/domain` holds
what a document, chunk, citation, review and activation gate mean; `rag/authoring`
retrieves and verifies.

`rag` imports `packages/shared` and nothing else from the repository: it never
reaches the clinical database, and it never sees a subject, a note or an
identifier.
"""
