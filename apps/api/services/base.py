"""Application service container."""

from __future__ import annotations

from typing import Any

from apps.api.adapters import Ports
from apps.api.canonical import canonical_timestamp
from apps.api.clock import Clock, system_clock
from apps.api.settings import Settings
from apps.api.store.db import Database


class Services:
    def __init__(
        self,
        *,
        settings: Settings,
        database: Database,
        ports: Ports,
        clock: Clock = system_clock,
        draft_transport: Any | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.ports = ports
        self.clock = clock
        self.draft_transport = draft_transport

    def now(self) -> str:
        return canonical_timestamp(self.clock())
