"""Request-scoped values for the fixed demo tenant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from tools.seed import ids

DEMO_TENANT_ID: Final[str] = str(ids.TENANT_A)


@dataclass(frozen=True, slots=True)
class RequestContext:
    tenant_id: str = DEMO_TENANT_ID
    request_id: str = ""
