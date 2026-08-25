"""Reloj inyectable (CONVENTIONS 16: "tests de tiempo usan reloj inyectado")."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    """Tiempo de servidor, siempre UTC y consciente de zona."""
    return datetime.now(UTC)


class FrozenClock:
    """Reloj de prueba que solo avanza cuando se le pide."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("un reloj de prueba necesita zona explícita")
        self._now = start.astimezone(UTC)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **delta: float) -> datetime:
        self._now = self._now + timedelta(**delta)
        return self._now

    def set(self, moment: datetime) -> datetime:
        self._now = moment.astimezone(UTC)
        return self._now
