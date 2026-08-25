"""Contract generation and provenance tooling.

`generate` renders JSON Schema and TypeScript/Zod from the Pydantic source of
truth in `packages/shared`. `source_evidence` renders a non-identifiable
manifest of the untracked evidence exports so the repository can cite counts and
hashes without ever versioning a clinical CSV.
"""
