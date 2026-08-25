"""What the contract publishes, and under which artifact name.

`registry.py` is hand-written and is the source of truth for *which* models are
part of the published contract. Everything under `packages/shared/generated/` is
derived from it and is never edited by hand.
"""

from packages.shared.schema.registry import (
    PUBLISHED_MODELS,
    SCHEMA_ARTIFACT,
    published_model,
)

__all__ = ["PUBLISHED_MODELS", "SCHEMA_ARTIFACT", "published_model"]
